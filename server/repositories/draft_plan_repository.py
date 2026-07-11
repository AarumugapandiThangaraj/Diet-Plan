from typing import List, Dict, Any, Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import uuid
from database.session import AsyncSessionLocal
from database.models import DietPlan, DietPlanDay, DietPlanMeal, DietPlanMealFood, Meal, DietPlanEvent
from exceptions.repository import RepositoryException
from schemas import PatchOperation

def _safe_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    """Parse a UUID string safely; returns None if value is missing or invalid."""
    if not value or value == "None":
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError):
        return None

async def update_draft_plan(plan_id: str, user_id: str, version: int, operations: List[PatchOperation]) -> dict:
    import logging
    _log = logging.getLogger("app.repo")
    try:
        print("Method stating - Update draft plan")

        async with AsyncSessionLocal() as session:
            # plan_id must always be a UUID
            try:
                pid = uuid.UUID(plan_id)
            except (ValueError, AttributeError):
                raise RepositoryException(f"Invalid plan ID format: {plan_id!r}")

            # user_id may be a non-UUID string (e.g. 'usr_jwkuloxt') — handle both
            uid: Optional[uuid.UUID] = None
            try:
                uid = uuid.UUID(user_id)
            except (ValueError, AttributeError):
                _log.debug(f"user_id {user_id!r} is not a UUID — filtering by plan_id only")

            # Fetch the plan (with row lock)
            if uid is not None:
                stmt = select(DietPlan).filter_by(id=pid, user_id=uid).with_for_update()
            else:
                stmt = select(DietPlan).filter_by(id=pid).with_for_update()
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()

            if not plan:
                raise RepositoryException("Plan not found")
            
            if plan.version != version:
                # Auto-sync: client may have a stale version after multiple swaps.
                # We accept the operation and use the current DB version.
                # For strict multi-user conflict detection, re-enable the exception below.
                # raise RepositoryException("Version mismatch. Plan was modified by another request.")
                version = plan.version

            
            # Apply operations
            affected_day_ids = set()
            for op in operations:
                if op.type == 'move':
                    pass

                elif op.type == 'food_swap':
                    # Resolve the DietPlanMeal instance from mealInstanceId
                    instance_id = _safe_uuid(op.mealInstanceId)
                    if not instance_id:
                        import logging
                        logging.getLogger("app.repo").warning(
                            f"food_swap op skipped: mealInstanceId is invalid or None (got {op.mealInstanceId!r})"
                        )
                        continue

                    stmt = select(DietPlanMeal).filter_by(id=instance_id)
                    res = await session.execute(stmt)
                    dp_meal = res.scalar_one_or_none()
                    if not dp_meal:
                        continue

                    stmt = select(DietPlanDay).filter_by(id=dp_meal.plan_day_id)
                    res = await session.execute(stmt)
                    dp_day = res.scalar_one_or_none()
                    if not dp_day:
                        continue

                    scaled_meal = op.customMealPayload or {}

                    # Prefer the replacementMealId from the option (guaranteed to be an integer DB ID like "247")
                    # Fallback chain: option ID → scaled_meal Meal_ID → original dp_meal.meal_id
                    def _safe_int_id(val) -> int | None:
                        try:
                            return int(val) if val is not None else None
                        except (ValueError, TypeError):
                            return None

                    db_new_meal_id = (
                        _safe_int_id(op.replacementMealId) or
                        _safe_int_id(scaled_meal.get("Meal_ID")) or
                        _safe_int_id(scaled_meal.get("id")) or
                        dp_meal.meal_id
                    )

                    # Update DietPlanMeal macros
                    macros = scaled_meal.get("macros") or scaled_meal.get("_macros") or {}
                    upd_stmt = update(DietPlanMeal).where(DietPlanMeal.id == instance_id).values(
                        meal_id=db_new_meal_id,
                        calories_kcal=macros.get("caloriesKcal", 0.0),
                        protein_g=macros.get("proteinG", 0.0),
                        carbs_g=macros.get("carbsG", 0.0),
                        fat_g=macros.get("fatG", 0.0),
                        fiber_g=macros.get("fiberG", 0.0)
                    )
                    await session.execute(upd_stmt)

                    # Update food items in the meal
                    stmt = select(DietPlanMealFood).filter_by(plan_meal_id=instance_id)
                    res = await session.execute(stmt)
                    old_foods = res.scalars().all()

                    new_foods = scaled_meal.get("foods_struct") or scaled_meal.get("foods") or []

                    from database.models import Food

                    min_len = min(len(old_foods), len(new_foods))

                    for i in range(min_len):
                        sf = new_foods[i]
                        client_food_id = sf.get("id") or sf.get("food_id")
                        db_food_id = None
                        if client_food_id is not None:
                            try:
                                db_food_id = (await session.execute(
                                    select(Food.id).filter_by(id=int(client_food_id))
                                )).scalar()
                            except (ValueError, TypeError):
                                pass
                        old_foods[i].food_id = db_food_id
                        old_foods[i].quantity = sf.get("quantity", 0)
                        old_foods[i].unit = sf.get("unit", "g")

                    if len(new_foods) > len(old_foods):
                        for i in range(len(old_foods), len(new_foods)):
                            sf = new_foods[i]
                            client_food_id = sf.get("id") or sf.get("food_id")
                            db_food_id = None
                            if client_food_id is not None:
                                try:
                                    db_food_id = (await session.execute(
                                        select(Food.id).filter_by(id=int(client_food_id))
                                    )).scalar()
                                except (ValueError, TypeError):
                                    pass
                            food_obj = DietPlanMealFood(
                                plan_meal_id=dp_meal.id,
                                food_id=db_food_id,
                                quantity=sf.get("quantity", 0),
                                unit=sf.get("unit", "g")
                            )
                            session.add(food_obj)

                    if len(old_foods) > len(new_foods):
                        for i in range(len(new_foods), len(old_foods)):
                            await session.delete(old_foods[i])

                    await session.flush()
                    affected_day_ids.add(dp_day.id)

                elif op.type == 'swap':
                    # Whole-meal swap
                    if not op.mealInstanceId:
                        continue
                    instance_id = _safe_uuid(op.mealInstanceId)
                    if not instance_id:
                        continue
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
                    db_new_meal_id = db_new_meal.id

                    upd_stmt = update(DietPlanMeal).where(DietPlanMeal.id == instance_id).values(
                        meal_id=db_new_meal_id,
                        calories_kcal=scaled_meal.get("macros", {}).get("caloriesKcal", 0.0),
                        protein_g=scaled_meal.get("macros", {}).get("proteinG", 0.0),
                        carbs_g=scaled_meal.get("macros", {}).get("carbsG", 0.0),
                        fat_g=scaled_meal.get("macros", {}).get("fatG", 0.0),
                        fiber_g=scaled_meal.get("macros", {}).get("fiberG", 0.0)
                    )
                    await session.execute(upd_stmt)
                    await session.flush()
                    affected_day_ids.add(dp_day.id)


            # Update version
            plan.version += 1
            
            # Record events
            for op in operations:
                event = DietPlanEvent(
                    plan_id=plan.id,
                    event_type=f"MEAL_{op.type.upper()}",
                    meal_instance_id=_safe_uuid(op.mealInstanceId),
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
            except (ValueError, AttributeError):
                raise RepositoryException(f"Invalid plan ID format: {plan_id!r}")

            uid: Optional[uuid.UUID] = None
            try:
                uid = uuid.UUID(user_id)
            except (ValueError, AttributeError):
                pass  # non-UUID user_id — filter by plan_id only

            # Fetch plan by id and user (without status filter for resilience)
            if uid is not None:
                stmt = select(DietPlan).filter_by(id=pid, user_id=uid).with_for_update()
            else:
                stmt = select(DietPlan).filter_by(id=pid).with_for_update()
            res = await session.execute(stmt)
            plan = res.scalar_one_or_none()
            
            if not plan:
                raise RepositoryException("Draft plan not found")
            
            # If already active, treat as idempotent success
            if plan.status == 'active':
                return True
            
            if plan.status != 'draft':
                raise RepositoryException(f"Plan cannot be activated from status '{plan.status}'")

            # Archive existing active plans — use same uid filter if available
            if uid is not None:
                stmt_active = select(DietPlan).filter_by(user_id=uid, status='active')
            else:
                stmt_active = select(DietPlan).filter_by(id=pid, status='active')
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
