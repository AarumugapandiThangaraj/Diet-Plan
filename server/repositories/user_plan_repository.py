from datetime import date
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models import DietPlan, DietPlanDay, DietPlanMeal, DietPlanMealFood, DietPlanMealFoodIngredient, MealSession, UserHealthProfile
from sqlalchemy.exc import SQLAlchemyError
from exceptions.repository import RepositoryException
import uuid

async def load_user_plan(user_identifier: str) -> Optional[dict]:
    """
    Asynchronously retrieves user plan by building the legacy plan_payload dictionary from V2 tables.
    """
    try:
        async with AsyncSessionLocal() as session:
            # We assume user_identifier can be matched to a DietPlan via the user_id (if valid UUID)
            # or we need to lookup user_id. For now, assuming user_identifier is a stringified UUID.
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
                    .selectinload(DietPlanMeal.meal_foods_rel)
                    .selectinload(DietPlanMealFood.ingredients_rel)
                    .selectinload(DietPlanMealFoodIngredient.ingredient),
                    selectinload(DietPlan.days_rel)
                    .selectinload(DietPlanDay.meals_rel)
                    .selectinload(DietPlanMeal.meal)
                )
            )
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
                        
                        # reconstruct meal dict
                        foods_struct = []
                        for pmf in pmeal.meal_foods_rel:
                            ingredients_struct = []
                            for pmfi in pmf.ingredients_rel:
                                ingredients_struct.append({
                                    "id": pmfi.ingredient_id,
                                    "name": pmfi.ingredient.name_en if pmfi.ingredient else "",
                                    "quantity": pmfi.quantity,
                                    "unit": pmfi.unit,
                                    "macros": {
                                        "caloriesKcal": float(pmfi.calories_kcal or 0),
                                        "proteinG": float(pmfi.protein_g or 0),
                                        "carbsG": float(pmfi.carbs_g or 0),
                                        "fatG": float(pmfi.fat_g or 0),
                                        "fiberG": float(pmfi.fiber_g or 0)
                                    }
                                })
                            foods_struct.append({
                                "id": pmf.food_id,
                                "name": pmf.food.name_en if pmf.food else "",
                                "preparation": pmf.food.preparation_en if pmf.food else "",
                                "quantity": pmf.quantity,
                                "unit": pmf.unit,
                                "ingredients_struct": ingredients_struct,
                                "macros": {
                                    "caloriesKcal": float(pmf.calories_kcal or 0),
                                    "proteinG": float(pmf.protein_g or 0),
                                    "carbsG": float(pmf.carbs_g or 0),
                                    "fatG": float(pmf.fat_g or 0),
                                    "fiberG": float(pmf.fiber_g or 0)
                                }
                            })
                            
                        macros_dict = {
                            "caloriesKcal": float(pmeal.calories_kcal or 0),
                            "proteinG": float(pmeal.protein_g or 0),
                            "carbsG": float(pmeal.carbs_g or 0),
                            "fatG": float(pmeal.fat_g or 0),
                            "fiberG": float(pmeal.fiber_g or 0)
                        }
                        day_dict[session_code] = {
                            "Meal_ID": pmeal.meal.client_meal_id if pmeal.meal else "",
                            "meal_name": pmeal.meal.name_en if pmeal.meal else "",
                            "image_ID": pmeal.meal.client_meal_id if pmeal.meal else "",
                            "foods_struct": foods_struct,
                            "macros": macros_dict,
                            "_macros": macros_dict
                        }
                    plans_arr.append(day_dict)
                    
                plan_payload = {
                    "days": plan_obj.days, # we named it days
                    "targets": {
                        "dailyCalories": float(plan_obj.target_calories_kcal or 0),
                        "proteinG": float(plan_obj.target_protein_g or 0),
                        "carbsG": float(plan_obj.target_carbs_g or 0),
                        "fatG": float(plan_obj.target_fat_g or 0),
                        "fiberG": float(plan_obj.target_fiber_g or 0),
                        "bmi": float(plan_obj.bmi_snapshot or 0),
                        "bmiCategory": plan_obj.bmi_category_snapshot or "",
                        "waterL": float(plan_obj.target_water_l or 0)
                    },
                    "totalsAll": {
                        "caloriesKcal": float(plan_obj.totals_calories_kcal or 0),
                        "proteinG": float(plan_obj.totals_protein_g or 0),
                        "carbsG": float(plan_obj.totals_carbs_g or 0),
                        "fatG": float(plan_obj.totals_fat_g or 0),
                        "fiberG": float(plan_obj.totals_fiber_g or 0)
                    },
                    "plans": plans_arr,
                    "mealTimes": list(plans_arr[0].keys()) if plans_arr else []
                }

                return {
                    "user_identifier": user_identifier,
                    "start_date": plan_obj.starts_on,
                    "end_date": plan_obj.ends_on,
                    "plan_payload": plan_payload
                }
            return None
    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load user plan from repository") from ex

async def save_user_plan(user_identifier: str, start_date: date, end_date: date, plan_payload: dict, profile_data: dict = None) -> dict:
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
            
            # fetch meals and foods to map client_ids to bigints
            from database.models import Meal, Food
            meal_stmt = select(Meal.client_meal_id, Meal.id)
            meal_res = await session.execute(meal_stmt)
            meals_map = {client_id: pk_id for client_id, pk_id in meal_res.all()}
            
            food_stmt = select(Food.client_food_id, Food.id)
            food_res = await session.execute(food_stmt)
            foods_map = {client_id: pk_id for client_id, pk_id in food_res.all()}

            # archive old plans
            stmt = select(DietPlan).filter_by(user_id=uid, status='active')
            res = await session.execute(stmt)
            old_plans = res.scalars().all()
            for op in old_plans:
                op.status = 'archived'
            await session.flush()
            targets = plan_payload.get("targets", {})
            totals = plan_payload.get("totalsAll") or plan_payload.get("totals", {})
            
            health_profile_id = None
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
                    age=profile_data.get("age"),
                    gender=profile_data.get("gender"),
                    height_cm=profile_data.get("heightCm"),
                    weight_kg=profile_data.get("weightKg"),
                    target_weight_kg=targets.get("targetWeightKg"),
                    bmi=targets.get("bmi"),
                    bmi_category=targets.get("bmiCategory"),
                    bmr_kcal=targets.get("bmr"),
                    tdee_kcal=targets.get("tdee"),
                    target_water_l=targets.get("waterL"),
                    activity_level=mapped_activity,
                    is_latest=True
                )
                session.add(uhp)
                await session.flush()
                health_profile_id = uhp.id
            
            plan_obj = DietPlan(
                user_id=uid,
                health_profile_id=health_profile_id,
                days=int(plan_payload.get("days", 1)),
                status='active',
                target_calories_kcal=int(targets.get("dailyCalories", 0)),
                target_protein_g=targets.get("proteinG"),
                target_protein_g_min=targets.get("proteinGMin"),
                target_protein_g_max=targets.get("proteinGMax"),
                target_carbs_g=targets.get("carbsG"),
                target_carbs_g_min=targets.get("carbsGMin"),
                target_carbs_g_max=targets.get("carbsGMax"),
                target_fat_g=targets.get("fatG"),
                target_fat_g_min=targets.get("fatGMin"),
                target_fat_g_max=targets.get("fatGMax"),
                target_fiber_g=targets.get("fiberG"),
                target_water_l=targets.get("waterL"),
                target_water_l_min=targets.get("waterLMin"),
                target_water_l_max=targets.get("waterLMax"),
                bmi_snapshot=targets.get("bmi"),
                bmi_category_snapshot=targets.get("bmiCategory"),
                bmr_kcal_snapshot=targets.get("bmr"),
                tdee_kcal_snapshot=targets.get("tdee"),
                activity_level_snapshot=profile_data.get("activityLevel") if profile_data else None,
                totals_calories_kcal=totals.get("caloriesKcal"),
                totals_protein_g=totals.get("proteinG"),
                totals_carbs_g=totals.get("carbsG"),
                totals_fat_g=totals.get("fatG"),
                totals_fiber_g=totals.get("fiberG"),
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
                    
                    meal_obj = DietPlanMeal(
                        plan_day_id=day_obj.id,
                        meal_session_id=sessions_map[session_code],
                        meal_id=meals_map.get(client_meal_id) if client_meal_id else None,
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
                        client_food_id = food_data.get("id")
                        
                        food_obj = DietPlanMealFood(
                            plan_meal_id=meal_obj.id,
                            food_id=foods_map.get(client_food_id) if client_food_id else None,
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
                        
                        for ing_data in food_data.get("ingredients_struct", []):
                            i_macros = ing_data.get("macros", {})
                            ing_id = ing_data.get("id")
                            
                            ing_obj = DietPlanMealFoodIngredient(
                                plan_meal_food_id=food_obj.id,
                                ingredient_id=int(ing_id) if str(ing_id).isdigit() else None, # ingredient IDs are already ints!
                                quantity=ing_data.get("quantity", 0),
                                unit=ing_data.get("unit", "g"),
                                calories_kcal=i_macros.get("caloriesKcal"),
                                protein_g=i_macros.get("proteinG"),
                                carbs_g=i_macros.get("carbsG"),
                                fat_g=i_macros.get("fatG"),
                                fiber_g=i_macros.get("fiberG")
                            )
                            session.add(ing_obj)
            
            await session.commit()
            
            return {
                "user_identifier": user_identifier,
                "start_date": start_date,
                "end_date": end_date,
                "plan_payload": plan_payload
            }
    except SQLAlchemyError as ex:
        import traceback
        import logging
        logging.getLogger("app.repo").error(f"SQLAlchemyError in save_user_plan:\n{traceback.format_exc()}")
        raise RepositoryException(f"Failed to save user plan: {str(ex)}") from ex
