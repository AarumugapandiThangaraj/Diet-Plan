from datetime import date
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models import DietPlan, DietPlanDay, DietPlanMeal, DietPlanMealFood, MealSession, UserHealthProfile
from utils.normalizers import _normalize_cuisine
from sqlalchemy.exc import SQLAlchemyError
from exceptions.repository import RepositoryException
import uuid

async def _load_plan_from_stmt(session, stmt) -> Optional[dict]:
    res = await session.execute(stmt)
    plan_obj = res.scalar_one_or_none()
    if plan_obj:
        # Fetch sessions for session codes
        sessions_stmt = select(MealSession)
        sessions_res = await session.execute(sessions_stmt)
        sessions_map = {s.id: s.code for s in sessions_res.scalars().all()}
        
        # Reconstruct legacy plan_payload
        plans_arr = []
        # sort days
        days_sorted = sorted(plan_obj.days_rel, key=lambda d: d.day_number)
        for day in days_sorted:
            day_dict = {}
            for pmeal in day.meals_rel:
                session_code = sessions_map.get(pmeal.meal_session_id)
                if not session_code: continue
                
                meal_dict = {
                    "id": str(pmeal.id),
                    "Meal_ID": pmeal.meal.id if pmeal.meal else None,
                    "name": pmeal.meal.recipe_name if pmeal.meal else None,
                    "macros": {
                        "caloriesKcal": float(pmeal.calories_kcal) if pmeal.calories_kcal else 0.0,
                        "proteinG": float(pmeal.protein_g) if pmeal.protein_g else 0.0,
                        "carbsG": float(pmeal.carbs_g) if pmeal.carbs_g else 0.0,
                        "fatG": float(pmeal.fat_g) if pmeal.fat_g else 0.0,
                        "fiberG": float(pmeal.fiber_g) if pmeal.fiber_g else 0.0
                    },
                    "foods_struct": []
                }
                
                for pfood in pmeal.meal_foods_rel:
                    food_dict = {
                        "id": pfood.food.id if pfood.food else None,
                        "name": pfood.food.food_name if pfood.food else None,
                        "quantity": float(pfood.quantity),
                        "unit": pfood.unit,
                        "macros": {
                            "caloriesKcal": float(pfood.calories_kcal) if pfood.calories_kcal else 0.0,
                            "proteinG": float(pfood.protein_g) if pfood.protein_g else 0.0,
                            "carbsG": float(pfood.carbs_g) if pfood.carbs_g else 0.0,
                            "fatG": float(pfood.fat_g) if pfood.fat_g else 0.0,
                            "fiberG": float(pfood.fiber_g) if pfood.fiber_g else 0.0
                        },
                        "ingredients_struct": []
                    }
                    
                    meal_dict["foods_struct"].append(food_dict)
                    
                day_dict[session_code] = meal_dict
            plans_arr.append(day_dict)
            
        plan_payload = {
            "days": plan_obj.days,
            "targets": {
                "dailyCalories": float(plan_obj.target_calories_kcal) if plan_obj.target_calories_kcal else 0.0,
                "proteinG": float(plan_obj.target_protein_g) if plan_obj.target_protein_g else 0.0,
                "carbsG": float(plan_obj.target_carbs_g) if plan_obj.target_carbs_g else 0.0,
                "fatG": float(plan_obj.target_fat_g) if plan_obj.target_fat_g else 0.0,
                "fiberG": float(plan_obj.target_fiber_g) if plan_obj.target_fiber_g else 0.0,
                "waterL": float(plan_obj.target_water_l) if plan_obj.target_water_l else 0.0
            },
            "plans": plans_arr,
            "totalsAll": {
                "caloriesKcal": float(plan_obj.totals_calories_kcal) if plan_obj.totals_calories_kcal else 0.0,
                "proteinG": float(plan_obj.totals_protein_g) if plan_obj.totals_protein_g else 0.0,
                "carbsG": float(plan_obj.totals_carbs_g) if plan_obj.totals_carbs_g else 0.0,
                "fatG": float(plan_obj.totals_fat_g) if plan_obj.totals_fat_g else 0.0,
                "fiberG": float(plan_obj.totals_fiber_g) if plan_obj.totals_fiber_g else 0.0
            }
        }
        
        return {
            "user_identifier": str(plan_obj.user_id),
            "start_date": plan_obj.starts_on,
            "end_date": plan_obj.ends_on,
            "plan_payload": plan_payload,
            "plan_id": str(plan_obj.id),
            "version": plan_obj.version,
            "status": plan_obj.status
        }
    return None

async def load_user_plan(user_identifier: str) -> Optional[dict]:
    """
    Asynchronously retrieves user plan by building the legacy plan_payload dictionary from V2 tables.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                return None

            stmt = (
                select(DietPlan)
                .filter_by(user_id=uid, status='active')
                .options(
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal_foods_rel)
                    .selectinload(DietPlanMealFood.food),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal_foods_rel),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal)
                )
            )
            return await _load_plan_from_stmt(session, stmt)
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user plan from repository") from ex

async def load_user_plan_by_id(plan_id: str) -> Optional[dict]:
    try:
        async with AsyncSessionLocal() as session:
            try:
                pid = uuid.UUID(plan_id)
            except ValueError:
                return None

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
                    .selectinload(DietPlanMeal.meal_foods_rel),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal)
                )
            )
            return await _load_plan_from_stmt(session, stmt)
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user plan by ID from repository") from ex

async def save_user_plan(user_identifier: str, start_date: date, end_date: date, plan_payload: dict, profile_data: dict = None, status: str = 'active') -> dict:
    """
    Asynchronously saves user plan by translating legacy plan_payload dict into V2 tables.
    Also creates UserHealthProfile if profile_data is provided.
    """
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                raise RepositoryException("Invalid user identifier format (expected UUID)")
                
            # fetch sessions
            sessions_stmt = select(MealSession)
            sessions_res = await session.execute(sessions_stmt)
            sessions_map = {s.code: s.id for s in sessions_res.scalars().all()}
            
            # fetch cuisines
            from database.models import Cuisine, Meal, Food
            cuisine_stmt = select(Cuisine.code, Cuisine.id)
            cuisine_res = await session.execute(cuisine_stmt)
            cuisine_map = {code.lower(): pk_id for code, pk_id in cuisine_res.all()}

            # fetch meals and foods to map (cuisine_id, client_ids) to bigints
            # Removed mapping logic as meal_id and food_id are now String(50)

            # only archive old plans if activating
            if status == 'active':
                stmt = select(DietPlan).filter_by(user_id=uid, status='active')
                res = await session.execute(stmt)
                old_plans = res.scalars().all()
                for op in old_plans:
                    op.status = 'archived'
                await session.flush()
            elif status == 'draft':
                # Archive or delete previous draft
                stmt = select(DietPlan).filter_by(user_id=uid, status='draft')
                res = await session.execute(stmt)
                old_drafts = res.scalars().all()
                for od in old_drafts:
                    await session.delete(od)
                await session.flush()
                
            targets = plan_payload.get("targets", {})
            totals = plan_payload.get("totalsAll") or plan_payload.get("totals", {})
            
            health_profile_id = None
            
            def _int(v): return int(float(v)) if v is not None and str(v).strip() else None
            def _float(v): return float(v) if v is not None and str(v).strip() else None

            if profile_data:
                await session.execute(
                    update(UserHealthProfile).where(UserHealthProfile.user_id == uid).values(is_latest=False)
                )
                activity_mapping = {
                    "sedentary": "sedentary",
                    "light": "lightly_active",
                    "moderate": "moderately_active",
                    "heavy": "very_active"
                }
                act_level = profile_data.get("activityLevel")
                mapped_activity = activity_mapping.get(act_level, act_level)

                uhp = UserHealthProfile(
                    user_id=uid,
                    age=_int(profile_data.get("age")),
                    gender=profile_data.get("gender"),
                    height_cm=_float(profile_data.get("heightCm")),
                    weight_kg=_float(profile_data.get("weightKg")),
                    target_weight_kg=_float(targets.get("targetWeightKg")),
                    bmi=_float(targets.get("bmi")),
                    bmi_category=targets.get("bmiCategory"),
                    bmr_kcal=_int(targets.get("bmr")),
                    tdee_kcal=_int(targets.get("tdee")),
                    target_water_l=_float(targets.get("waterL")),
                    activity_level=mapped_activity,
                    is_latest=True
                )
                session.add(uhp)
                await session.flush()
                health_profile_id = uhp.id
            
            plan_obj = DietPlan(
                user_id=uid,
                health_profile_id=health_profile_id,
                days=_int(plan_payload.get("days", 1)),
                status=status,
                target_calories_kcal=_int(targets.get("dailyCalories", 0)),
                target_protein_g=_float(targets.get("proteinG")),
                target_protein_g_min=_float(targets.get("proteinGMin")),
                target_protein_g_max=_float(targets.get("proteinGMax")),
                target_carbs_g=_float(targets.get("carbsG")),
                target_carbs_g_min=_float(targets.get("carbsGMin")),
                target_carbs_g_max=_float(targets.get("carbsGMax")),
                target_fat_g=_float(targets.get("fatG")),
                target_fat_g_min=_float(targets.get("fatGMin")),
                target_fat_g_max=_float(targets.get("fatGMax")),
                target_fiber_g=_float(targets.get("fiberG")),
                target_water_l=_float(targets.get("waterL")),
                target_water_l_min=_float(targets.get("waterLMin")),
                target_water_l_max=_float(targets.get("waterLMax")),
                bmi_snapshot=_float(targets.get("bmi")),
                bmi_category_snapshot=targets.get("bmiCategory"),
                bmr_kcal_snapshot=_int(targets.get("bmr")),
                tdee_kcal_snapshot=_int(targets.get("tdee")),
                activity_level_snapshot=profile_data.get("activityLevel") if profile_data else None,
                totals_calories_kcal=_float(totals.get("caloriesKcal")),
                totals_protein_g=_float(totals.get("proteinG")),
                totals_carbs_g=_float(totals.get("carbsG")),
                totals_fat_g=_float(totals.get("fatG")),
                totals_fiber_g=_float(totals.get("fiberG")),
                starts_on=start_date,
                ends_on=end_date
            )
            session.add(plan_obj)
            await session.flush() # get plan_obj.id
            
            plans_arr = plan_payload.get("plans")
            if not plans_arr:
                single_plan = plan_payload.get("plan")
                if single_plan:
                    plans_arr = [single_plan]
                else:
                    plans_arr = []
                    
            for day_idx, day_data in enumerate(plans_arr):
                day_obj = DietPlanDay(
                    plan_id=plan_obj.id,
                    day_number=day_idx + 1
                )
                session.add(day_obj)
                await session.flush()
                
                for session_code, meal_data in day_data.items():
                    if session_code not in sessions_map: continue
                    meal_macros = meal_data.get("macros") or meal_data.get("_macros") or {}
                    
                    client_meal_id = meal_data.get("Meal_ID")
                    
                    meal_cuisine_name = _normalize_cuisine(meal_data.get("cuisine_type") or profile_data.get("cuisineType") or "continental")
                    c_id = cuisine_map.get(meal_cuisine_name)

                    meal_obj = DietPlanMeal(
                        plan_day_id=day_obj.id,
                        meal_session_id=sessions_map[session_code],
                        meal_id=str(client_meal_id) if client_meal_id else None,
                        calories_kcal=meal_macros.get("caloriesKcal"),
                        protein_g=meal_macros.get("proteinG"),
                        carbs_g=meal_macros.get("carbsG"),
                        fat_g=meal_macros.get("fatG"),
                        fiber_g=meal_macros.get("fiberG")
                    )
                    session.add(meal_obj)
                    await session.flush()
                    
                    for food_data in meal_data.get("foods_struct", []):
                        f_macros = food_data.get("macros", {})
                        client_food_id = str(food_data.get("id")) if food_data.get("id") is not None else None
                        
                        food_obj = DietPlanMealFood(
                            plan_meal_id=meal_obj.id,
                            food_id=str(client_food_id) if client_food_id else None,
                            quantity=food_data.get("quantity", 0),
                            unit=food_data.get("unit", "g"),
                            calories_kcal=f_macros.get("caloriesKcal"),
                            protein_g=f_macros.get("proteinG"),
                            carbs_g=f_macros.get("carbsG"),
                            fat_g=f_macros.get("fatG"),
                            fiber_g=f_macros.get("fiberG")
                        )
                        session.add(food_obj)
                        await session.flush()
            
            await session.commit()
            
            return {
                "user_identifier": user_identifier,
                "start_date": start_date,
                "end_date": end_date,
                "plan_payload": plan_payload,
                "plan_id": str(plan_obj.id),
                "version": plan_obj.version,
                "status": plan_obj.status
            }
    except SQLAlchemyError as ex:
        import traceback
        import logging
        logging.getLogger("app.repo").error(f"SQLAlchemyError in save_user_plan:\n{traceback.format_exc()}")
        raise RepositoryException(f"Failed to save user plan: {str(ex)}") from ex

async def load_latest_user_plan(user_identifier: str) -> Optional[dict]:
    try:
        async with AsyncSessionLocal() as session:
            try:
                uid = uuid.UUID(user_identifier)
            except ValueError:
                return None

            stmt = (
                select(DietPlan)
                .filter_by(user_id=uid)
                .filter(DietPlan.status.in_(['active', 'draft']))
                .order_by(DietPlan.created_at.desc())
                .limit(1)
                .options(
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal_foods_rel)
                    .selectinload(DietPlanMealFood.food),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal_foods_rel),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal)
                )
            )
            return await _load_plan_from_stmt(session, stmt)
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load latest user plan from repository") from ex
