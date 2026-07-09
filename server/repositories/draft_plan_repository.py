from typing import List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import uuid
from database.session import AsyncSessionLocal
from database.models import DietPlan, DietPlanDay, DietPlanMeal, DietPlanMealFood, Meal, DietPlanEvent
from exceptions.repository import RepositoryException
from schemas import PatchOperation

async def update_draft_plan(plan_id: str, user_id: str, version: int, operations: List[PatchOperation]) -> dict:
    try:
        async with AsyncSessionLocal() as session:
            try:
                pid = uuid.UUID(plan_id)
                uid = uuid.UUID(user_id)
            except ValueError:
                raise RepositoryException("Invalid ID format")

            # Start transaction explicitly if not already started
            # Fetch the draft plan
            stmt = select(DietPlan).filter_by(id=pid, user_id=uid, status='draft').with_for_update()
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()

            if not plan:
                raise RepositoryException("Draft plan not found")
            
            if plan.version != version:
                raise RepositoryException("Version mismatch. Plan was modified by another request.")
            
            # Apply operations
            affected_day_ids = set()
            for op in operations:
                if op.type == 'move':
                    pass
                elif op.type == 'swap':
                    instance_id = uuid.UUID(op.mealInstanceId)
                    new_meal_id = op.replacementMealId
                    
                    stmt = select(DietPlanMeal).filter_by(id=instance_id)
                    res = await session.execute(stmt)
                    dp_meal = res.scalar_one_or_none()
                    if not dp_meal:
                        continue
                        
                    stmt = select(DietPlanDay).filter_by(id=dp_meal.plan_day_id)
                    res = await session.execute(stmt)
                    dp_day = res.scalar_one_or_none()
                    
                    from database.models import MealSession
                    stmt = select(MealSession).filter_by(id=dp_meal.meal_session_id)
                    res = await session.execute(stmt)
                    m_session = res.scalar_one_or_none()
                    
                    if not dp_day or not m_session:
                        continue
                        
                    from database.models import Meal, Cuisine
                    stmt = select(Meal, Cuisine).join(Cuisine, Meal.cuisine_id == Cuisine.id).filter(Meal.id == int(new_meal_id))
                    res = await session.execute(stmt)
                    row = res.first()
                    if not row:
                        continue
                        
                    db_new_meal, db_cuisine = row
                    cuisine_code = db_cuisine.code
                    
                    from repositories.meal_repository import get_meal_index_by_id_async
                    idx = await get_meal_index_by_id_async(cuisine_code)
                    new_meal = idx.get(new_meal_id)
                    if not new_meal:
                        continue
                        
                    from services.ranking_service import session_target_macros
                    
                    targets = {
                        "caloriesKcal": float(plan.target_calories_kcal or 2000),
                        "proteinG": float(plan.target_protein_g or 100),
                        "carbsG": float(plan.target_carbs_g or 250),
                        "fatG": float(plan.target_fat_g or 60),
                        "fiberG": float(plan.target_fiber_g or 30)
                    }
                    sess_targets = session_target_macros(targets, m_session.code)
                    
                    from domain.scaling_formulas import scale_meal_to_targets
                    scale_info = scale_meal_to_targets(new_meal, sess_targets)
                    scaled_meal = scale_info["scaledMeal"]
                    
                    stmt = select(DietPlanMealFood).filter_by(plan_meal_id=instance_id)
                    res = await session.execute(stmt)
                    old_foods = res.scalars().all()
                    for f in old_foods:
                        await session.delete(f)
                        
                    dp_meal.meal_id = db_new_meal.id
                    meal_macros = scaled_meal.get("_macros") or scaled_meal.get("macros") or {}
                    dp_meal.calories_kcal = meal_macros.get("caloriesKcal", 0.0)
                    dp_meal.protein_g = meal_macros.get("proteinG", 0.0)
                    dp_meal.carbs_g = meal_macros.get("carbsG", 0.0)
                    dp_meal.fat_g = meal_macros.get("fatG", 0.0)
                    dp_meal.fiber_g = meal_macros.get("fiberG", 0.0)
                    
                    from database.models import Food
                    for sf in scaled_meal.get("foods_struct", []):
                        client_food_id = int(sf.get("id")) if sf.get("id") is not None else None
                        
                        stmt = select(Food.id).filter_by(id=client_food_id)
                        db_food_id = (await session.execute(stmt)).scalar()
                        
                        food_obj = DietPlanMealFood(
                            plan_meal_id=dp_meal.id,
                            food_id=db_food_id,
                            quantity=sf.get("quantity", 0),
                            unit=sf.get("unit", "g")
                        )
                        session.add(food_obj)
                        await session.flush()
                        
                    affected_day_ids.add(dp_day.id)

            # Update version
            plan.version += 1
            
            # Record events
            for op in operations:
                event = DietPlanEvent(
                    plan_id=plan.id,
                    event_type=f"MEAL_{op.type.upper()}",
                    meal_instance_id=uuid.UUID(op.mealInstanceId) if op.mealInstanceId else None,
                    details=op.model_dump()
                )
                session.add(event)
                
            await session.flush()
            from sqlalchemy.sql import func
            for d_id in affected_day_ids:
                stmt_agg = select(
                    func.sum(DietPlanMeal.calories_kcal).label('cals'),
                    func.sum(DietPlanMeal.protein_g).label('pro'),
                    func.sum(DietPlanMeal.carbs_g).label('carbs'),
                    func.sum(DietPlanMeal.fat_g).label('fat'),
                    func.sum(DietPlanMeal.fiber_g).label('fib')
                ).where(DietPlanMeal.plan_day_id == d_id)
                res_agg = await session.execute(stmt_agg)
                agg = res_agg.fetchone()
                
                upd_stmt = update(DietPlanDay).where(DietPlanDay.id == d_id).values(
                    calories_kcal=agg.cals or 0.0,
                    protein_g=agg.pro or 0.0,
                    carbs_g=agg.carbs or 0.0,
                    fat_g=agg.fat or 0.0,
                    fiber_g=agg.fib or 0.0
                )
                await session.execute(upd_stmt)

            await session.commit()
            
            # Re-fetch the updated plan to return
            from repositories.user_plan_repository import _load_plan_from_stmt
            stmt = (
                select(DietPlan)
                .filter_by(id=pid)
                .options(
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal_foods_rel)
                    .selectinload(DietPlanMealFood.food),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal)
                )
            )
            return await _load_plan_from_stmt(session, stmt)

    except RepositoryException:
        raise
    except Exception as e:
        import traceback, logging
        logging.getLogger("app.repo").error(f"Failed to update draft plan:\n{traceback.format_exc()}")
        raise RepositoryException(f"Failed to update draft plan: {str(e)}")

async def activate_draft_plan(plan_id: str, user_id: str) -> bool:
    try:
        async with AsyncSessionLocal() as session:
            try:
                pid = uuid.UUID(plan_id)
                uid = uuid.UUID(user_id)
            except ValueError:
                raise RepositoryException("Invalid ID format")

            # Fetch plan by id and user (without status filter for resilience)
            stmt = select(DietPlan).filter_by(id=pid, user_id=uid).with_for_update()
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()
            
            if not plan:
                raise RepositoryException("Draft plan not found")
            
            # If already active, treat as idempotent success
            if plan.status == 'active':
                return True
            
            if plan.status != 'draft':
                raise RepositoryException(f"Plan cannot be activated from status '{plan.status}'")

            # Archive existing active plans
            stmt_active = select(DietPlan).filter_by(user_id=uid, status='active')
            res_active = await session.execute(stmt_active)
            for active_plan in res_active.scalars().all():
                active_plan.status = 'archived'
            
            await session.flush()

            # Set new plan to active
            plan.status = 'active'
            
            # Record event
            event = DietPlanEvent(
                plan_id=plan.id,
                event_type="PLAN_ACTIVATED",
                # details={"version": version}
            )
            session.add(event)

            await session.commit()
            return True

    except RepositoryException:
        raise
    except Exception as e:
        import traceback, logging
        logging.getLogger("app.repo").error(f"Failed to activate draft plan:\n{traceback.format_exc()}")
        raise RepositoryException(f"Failed to activate draft plan: {str(e)}")

async def apply_meal_swap_to_db(plan_meal_id: str, new_meal_id: str, cuisine_type: str, macros: dict, scale_factor: float) -> bool:
    from database.session import AsyncSessionLocal
    from database.models import DietPlanMeal, DietPlanMealFood
    from sqlalchemy import select, delete
    import uuid
    from repositories.meal_repository import get_meal_index_by_id_async
    from exceptions.repository import RepositoryException
    
    try:
        pid = uuid.UUID(plan_meal_id)
    except ValueError:
        raise RepositoryException("Invalid planMealId format")
        
    idx = await get_meal_index_by_id_async(cuisine_type)
    new_meal = idx.get(str(new_meal_id))
    if not new_meal:
        raise RepositoryException(f"Meal {new_meal_id} not found in {cuisine_type} catalog")
        
    async with AsyncSessionLocal() as session:
        stmt = select(DietPlanMeal).filter_by(id=pid).with_for_update()
        res = await session.execute(stmt)
        dp_meal = res.scalar_one_or_none()
        if not dp_meal:
            raise RepositoryException("Meal instance not found in database")
            
        try:
            dp_meal.meal_id = int(new_meal_id)
        except ValueError:
            dp_meal.meal_id = None
        dp_meal.calories_kcal = macros.get("caloriesKcal", 0.0)
        dp_meal.protein_g = macros.get("proteinG", 0.0)
        dp_meal.carbs_g = macros.get("carbsG", 0.0)
        dp_meal.fat_g = macros.get("fatG", 0.0)
        dp_meal.fiber_g = macros.get("fiberG", 0.0)
        dp_meal.scale_applied = scale_factor
        
        stmt_del = delete(DietPlanMealFood).where(DietPlanMealFood.plan_meal_id == pid)
        await session.execute(stmt_del)
        
        foods = new_meal.get("foods_struct", [])
        for food in foods:
            food_obj = DietPlanMealFood(
                plan_meal_id=pid,
                unit=food.get("unit", "serving"),
                quantity=float(food.get("quantity", 1.0)) * scale_factor,
            )
            session.add(food_obj)
            
        await session.commit()
        return True
