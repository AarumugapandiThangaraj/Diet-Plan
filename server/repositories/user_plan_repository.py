from datetime import date
from typing import Optional
from sqlalchemy import select, update, delete, and_, func, String, cast, desc, text
from sqlalchemy.orm import selectinload, undefer
from database.session import AsyncSessionLocal
from database.models import DietPlan, DietPlanDay, DietPlanMeal, DietPlanMealFood, MealSession, UserHealthProfile, Meal
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
        totals_by_day_arr = []
        day_ids_arr = []
        # sort days
        days_sorted = sorted(plan_obj.days_rel, key=lambda d: d.day_number)
        for day in days_sorted:
            day_ids_arr.append(str(day.id))
            totals_by_day_arr.append({
                "caloriesKcal": float(day.calories_kcal) if day.calories_kcal else 0.0,
                "proteinG": float(day.protein_g) if day.protein_g else 0.0,
                "carbsG": float(day.carbs_g) if day.carbs_g else 0.0,
                "fatG": float(day.fat_g) if day.fat_g else 0.0,
                "fiberG": float(day.fiber_g) if day.fiber_g else 0.0
            })
            day_dict = {}
            for pmeal in day.meals_rel:
                session_code = sessions_map.get(pmeal.meal_session_id)
                if not session_code: continue
                
                meal_dict = {
                    "id": str(pmeal.id),
                    "Meal_ID": str(pmeal.meal.id) if pmeal.meal else None,
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
                        "id": str(pfood.food.id) if pfood.food else None,
                        "food_instance_id": str(pfood.id),
                        "name": pfood.food.food_name if pfood.food else None,
                        "quantity": float(pfood.quantity),
                        "unit": pfood.unit
                    }
                    
                    meal_dict["foods_struct"].append(food_dict)
                    
                day_dict[session_code] = meal_dict
            plans_arr.append(day_dict)
            
        plan_payload = {
            "days": plan_obj.days,
            "dayIds": day_ids_arr,
            "targets": {
                "dailyCalories": float(plan_obj.target_calories_kcal) if plan_obj.target_calories_kcal else 0.0,
                "proteinG": float(plan_obj.target_protein_g) if plan_obj.target_protein_g else 0.0,
                "carbsG": float(plan_obj.target_carbs_g) if plan_obj.target_carbs_g else 0.0,
                "fatG": float(plan_obj.target_fat_g) if plan_obj.target_fat_g else 0.0,
                "fiberG": float(plan_obj.target_fiber_g) if plan_obj.target_fiber_g else 0.0,
                "waterL": float(plan_obj.target_water_l) if plan_obj.target_water_l else 0.0
            },
            "plans": plans_arr,
            "totalsByDay": totals_by_day_arr,
            "totalsAll": {
                "caloriesKcal": float(plan_obj.totals_calories_kcal) if plan_obj.totals_calories_kcal else 0.0,
                "proteinG": float(plan_obj.totals_protein_g) if plan_obj.totals_protein_g else 0.0,
                "carbsG": float(plan_obj.totals_carbs_g) if plan_obj.totals_carbs_g else 0.0,
                "fatG": float(plan_obj.totals_fat_g) if plan_obj.totals_fat_g else 0.0,
                "fiberG": float(plan_obj.totals_fiber_g) if plan_obj.totals_fiber_g else 0.0
            }
        }
        
        # If it's a single day plan, surface the top-level keys expected
        if plan_obj.days == 1:
            plan_payload["plan"] = plans_arr[0] if plans_arr else {}
            plan_payload["totals"] = totals_by_day_arr[0] if totals_by_day_arr else {}
        
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
                archive_stmt = update(DietPlan).where(DietPlan.user_id == uid, DietPlan.status == 'active').values(status='archived')
                await session.execute(archive_stmt)
            elif status == 'draft':
                delete_stmt = delete(DietPlan).where(DietPlan.user_id == uid, DietPlan.status == 'draft')
                await session.execute(delete_stmt)
                
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
                    "lightly_active": "lightly_active",
                    "moderate": "moderately_active",
                    "moderately_active": "moderately_active",
                    "heavy": "very_active",
                    "very_active": "very_active",
                    "active": "very_active",
                    "extra_active": "extra_active"
                }
                act_level = profile_data.get("activityLevel")
                mapped_activity = activity_mapping.get(act_level, "very_active")

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
            
            plans_arr = plan_payload.get("plans")
            if not plans_arr:
                single_plan = plan_payload.get("plan")
                if single_plan:
                    plans_arr = [single_plan]
                else:
                    plans_arr = []
                    
            for day_idx, day_data in enumerate(plans_arr):
                day_obj = DietPlanDay(
                    day_number=day_idx + 1,
                    calories_kcal=0.0,
                    protein_g=0.0,
                    carbs_g=0.0,
                    fat_g=0.0,
                    fiber_g=0.0
                )
                plan_obj.days_rel.append(day_obj)
                
                for session_code, meal_data in day_data.items():
                    if session_code not in sessions_map: continue
                    meal_macros = meal_data.get("macros") or meal_data.get("_macros") or {}
                    
                    day_obj.calories_kcal += meal_macros.get("caloriesKcal", 0.0)
                    day_obj.protein_g += meal_macros.get("proteinG", 0.0)
                    day_obj.carbs_g += meal_macros.get("carbsG", 0.0)
                    day_obj.fat_g += meal_macros.get("fatG", 0.0)
                    day_obj.fiber_g += meal_macros.get("fiberG", 0.0)
                    
                    client_meal_id = meal_data.get("Meal_ID")
                    
                    meal_cuisine_name = _normalize_cuisine(meal_data.get("cuisine_type") or profile_data.get("cuisineType") or "continental")
                    c_id = cuisine_map.get(meal_cuisine_name)

                    meal_obj = DietPlanMeal(
                        meal_session_id=sessions_map[session_code],
                        meal_id=int(client_meal_id) if client_meal_id else None,
                        calories_kcal=meal_macros.get("caloriesKcal"),
                        protein_g=meal_macros.get("proteinG"),
                        carbs_g=meal_macros.get("carbsG"),
                        fat_g=meal_macros.get("fatG"),
                        fiber_g=meal_macros.get("fiberG"),
                        scale_applied=meal_data.get("scale", {}).get("applied", 1.0)
                    )
                    day_obj.meals_rel.append(meal_obj)
                    
                    for food_data in meal_data.get("foods_struct", []):
                        client_food_id = str(food_data.get("id")) if food_data.get("id") is not None else None
                        
                        base_size = float(food_data.get("serving_size") or 1.0)
                        scale_val = float(food_data.get("quantity") or 1.0)
                        scaled_qty = base_size * scale_val
                        
                        food_obj = DietPlanMealFood(
                            food_id=int(client_food_id) if client_food_id is not None else None,
                            quantity=scaled_qty,
                            unit=food_data.get("unit", "g")
                        )
                        meal_obj.meal_foods_rel.append(food_obj)
            
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
                .order_by(DietPlan.status.asc(), DietPlan.created_at.desc())
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

async def get_meal_instance_details(meal_instance_id: str, user_id: str) -> Optional[dict]:
    try:
        async with AsyncSessionLocal() as session:
            try:
                m_id = uuid.UUID(meal_instance_id)
                u_id = uuid.UUID(user_id)
            except ValueError:
                return None

            # Load the DietPlanMeal and its related plan and foods. We DO NOT selectinload(meal) 
            # because the Meal model schema is currently broken/out of sync with the database.
            stmt = (
                select(DietPlanMeal)
                .filter(DietPlanMeal.id == m_id)
                .options(
                    selectinload(DietPlanMeal.day).selectinload(DietPlanDay.plan),
                    selectinload(DietPlanMeal.meal_foods_rel)
                )
            )
            res = await session.execute(stmt)
            pmeal = res.scalar_one_or_none()
            
            if not pmeal:
                return None
                
            # Validate user
            if pmeal.day.plan.user_id != u_id:
                return {"error": "forbidden"}
                
            # Get meal session name
            session_stmt = select(MealSession).filter(MealSession.id == pmeal.meal_session_id)
            session_res = await session.execute(session_stmt)
            meal_session = session_res.scalar_one_or_none()
            meal_time = meal_session.name_en if meal_session else "Unknown"

            scale_factor = float(pmeal.scale_applied) if pmeal.scale_applied is not None else 1.0
            
            plan_status = pmeal.day.plan.status
            can_modify = plan_status in ['draft', 'active']

            # Safely query the broken meals table using raw SQL
            meal_name = "Custom Meal"
            image = None
            prep_instructions = []
            meal_id_str = pmeal.meal_id if pmeal.meal_id else ""
            
            if pmeal.meal_id:
                try:
                    # The DB has meals.id (bigint) and meals.client_meal_id (varchar)
                    # We check both to be safe
                    raw_meal_stmt = text(
                        'SELECT name_en, description_en FROM "Twellr_Nutri".meals '
                        'WHERE client_meal_id = :mid OR id::text = :mid LIMIT 1'
                    )
                    raw_res = await session.execute(raw_meal_stmt, {"mid": str(pmeal.meal_id)})
                    raw_meal = raw_res.fetchone()
                    if raw_meal:
                        if raw_meal[0]: meal_name = raw_meal[0]
                        if raw_meal[1]: prep_instructions = [raw_meal[1]] # Store description as an instruction
                except Exception as e:
                    import logging
                    logging.getLogger("app.repo").warning(f"Could not load raw meal data: {e}")

            # Ingredients mapping (using DietPlanMealFood since meal_ingredients table doesn't exist)
            ingredients = []
            
            # Fetch food names manually to bypass broken Food model
            food_ids = [mf.food_id for mf in pmeal.meal_foods_rel if mf.food_id]
            food_name_map = {}
            if food_ids:
                try:
                    # 'foods' table uses name_en instead of food_name
                    food_stmt = text('SELECT id, name_en FROM "Twellr_Nutri".foods WHERE id::bigint = ANY(:fids)')
                    fids_int = []
                    for fid in food_ids:
                        if isinstance(fid, int) or (isinstance(fid, str) and fid.isdigit()):
                            fids_int.append(int(fid))
                    # Fallback if the IDs are strings or bigints
                    food_res = await session.execute(food_stmt, {"fids": fids_int if fids_int else [-1]})
                    for row in food_res:
                        food_name_map[str(row[0])] = row[1]
                except Exception as e:
                    import logging
                    logging.getLogger("app.repo").warning(f"Could not load raw food data: {e}")

            for mf in pmeal.meal_foods_rel:
                food_id_str = str(mf.food_id) if mf.food_id else ""
                food_name = food_name_map.get(food_id_str, "Unknown Food")
                ingredients.append({
                    "ingredientId": food_id_str if food_id_str else str(mf.id),
                    "ingredientName": food_name,
                    "quantity": float(mf.quantity) * scale_factor,
                    "unit": mf.unit or "g"
                })

            return {
                "mealInstanceId": str(pmeal.id),
                "mealId": str(meal_id_str),
                "mealName": meal_name,
                "image": image,
                "mealTime": meal_time,
                "dayNumber": pmeal.day.day_number if pmeal.day else 1,
                "servingSize": "1 serving",
                "scaleFactor": scale_factor,
                "nutrition": {
                    "calories": int(pmeal.calories_kcal) if pmeal.calories_kcal else 0,
                    "protein": float(pmeal.protein_g) if pmeal.protein_g else 0.0,
                    "carbs": float(pmeal.carbs_g) if pmeal.carbs_g else 0.0,
                    "fat": float(pmeal.fat_g) if pmeal.fat_g else 0.0,
                    "fiber": float(pmeal.fiber_g) if pmeal.fiber_g else 0.0
                },
                "ingredients": ingredients,
                "preparation": {
                    "prepTime": 0,
                    "cookTime": 0,
                    "totalTime": 0,
                    "instructions": prep_instructions
                },
                "personalization": {
                    "whyThisMeal": "",
                    "nutritionNotes": "",
                    "recommendationReason": ""
                },
                "permissions": {
                    "canSwap": can_modify,
                    "canRearrange": can_modify,
                    "canCustomize": can_modify
                }
            }
    except SQLAlchemyError as ex:
        import traceback
        import logging
        logging.getLogger("app.repo").error(f"SQLAlchemyError in get_meal_instance_details:\n{traceback.format_exc()}")
        raise RepositoryException(f"Failed to load meal instance: {str(ex)}") from ex


async def load_plan_meal_recipe(plan_meal_id: uuid.UUID) -> Optional[dict]:
    try:
        async with AsyncSessionLocal() as session:
            from database.models import DietPlanMeal, DietPlanMealFood, Meal, MealIngredient, MealFood
            stmt = (
                select(DietPlanMeal)
                .filter(DietPlanMeal.id == plan_meal_id)
                .options(
                    selectinload(DietPlanMeal.meal).options(
                        selectinload(Meal.meal_ingredients),
                        selectinload(Meal.meal_foods).selectinload(MealFood.food),
                        undefer(Meal.preparation_steps),
                        undefer(Meal.time),
                        undefer(Meal.image)
                    ),
                    selectinload(DietPlanMeal.meal_foods_rel).selectinload(DietPlanMealFood.food)
                )
            )
            res = await session.execute(stmt)
            plan_meal = res.scalars().first()
            if not plan_meal or not plan_meal.meal:
                return None

            meal = plan_meal.meal

            # Calculate scaling factor
            meal_calories = float(meal.calories_kcal) if meal.calories_kcal else 0.0
            planned_calories = float(plan_meal.calories_kcal) if plan_meal.calories_kcal else 0.0
            
            scale_factor = 1.0
            if plan_meal.scale_applied is not None and float(plan_meal.scale_applied) > 0:
                scale_factor = float(plan_meal.scale_applied)
            elif meal_calories > 0 and planned_calories > 0:
                scale_factor = planned_calories / meal_calories

            # Parse serving sizes helper
            import re
            def parse_serving_size(serving_str: str):
                if not serving_str:
                    return 1.0, "serving"
                num_match = re.search(r"[\d\.]+", serving_str)
                unit_match = re.search(r"[a-zA-Z]+", serving_str)
                base_qty = float(num_match.group(0)) if num_match else 1.0
                unit = unit_match.group(0) if unit_match else "serving"
                return base_qty, unit

            # Helper to get prep time string
            def get_prep_time(time_str: str) -> str:
                if not time_str:
                    return "30 mins prep"
                match = re.findall(r"(\d{2}):(\d{2})", time_str)
                if len(match) == 2:
                    h1, m1 = map(int, match[0])
                    h2, m2 = map(int, match[1])
                    diff = (h2 * 60 + m2) - (h1 * 60 + m1)
                    if diff > 0:
                        return f"{diff} mins prep"
                if "min" in time_str.lower():
                    return time_str
                return "30 mins prep"

            # Parse foods
            foods = []
            for pfood in plan_meal.meal_foods_rel:
                food_id = pfood.food_id
                food_name = pfood.food.food_name if pfood.food else "Unknown"
                
                base_qty = 1.0
                unit = pfood.unit or "g"
                for mf in meal.meal_foods:
                    if mf.food_id == food_id:
                        base_qty = float(mf.serving_size) if mf.serving_size is not None else 1.0
                        break
                
                scaled_qty = base_qty * scale_factor
                foods.append({
                    "food_instance_id": str(pfood.id),
                    "food_id": food_id,
                    "food_name": food_name,
                    "quantity": scaled_qty,
                    "unit": unit,
                    "ingredients": [],
                    "prep_steps": []
                })

            if not foods:
                return None

            # Calculate proportional calories
            total_calories = float(plan_meal.calories_kcal) if plan_meal.calories_kcal else 0.0
            food_calories = int(round(total_calories / len(foods)))

            # Match scoring function
            def compute_match_score(text: str, food_name_str: str) -> float:
                text_lower = text.lower()
                food_lower = food_name_str.lower()
                if food_lower in text_lower or text_lower in food_lower:
                    return 10.0 + len(food_lower)
                words_text = set(re.findall(r"\b\w{3,}\b", text_lower))
                words_food = set(re.findall(r"\b\w{3,}\b", food_lower))
                overlap = words_text.intersection(words_food)
                if overlap:
                    return float(len(overlap))
                return 0.0

            # Partition preparation steps
            prep_steps = meal.preparation_steps or []
            if len(foods) == 1:
                foods[0]["prep_steps"] = list(prep_steps)
            elif len(foods) > 1:
                for step in prep_steps:
                    best_score = -1.0
                    best_food = None
                    for f in foods:
                        score = compute_match_score(step, f["food_name"])
                        if score > best_score:
                            best_score = score
                            best_food = f
                    if best_score <= 0 or best_food is None:
                        best_food = foods[0]
                    best_food["prep_steps"].append(step)

            # Scaled flat list of ingredients for the entire meal
            ingredients = [
                {
                    "name": mi.ingredient_name,
                    "quantity": round(float(mi.quantity) * scale_factor, 0),
                    "unit": mi.unit or "g"
                }
                for mi in meal.meal_ingredients
            ]

            # Format food list
            foods_struct = []
            for f in foods:
                foods_struct.append({
                    "food_instance_id": f["food_instance_id"],
                    "food_id": f["food_id"],
                    "food_name": f["food_name"],
                    "quantity": f["quantity"],
                    "unit": f["unit"]
                })

            total_quantity = sum(float(f["quantity"]) for f in foods) if foods else scale_factor

            recipe_details = {
                "mealInstanceId": str(plan_meal.id),
                "meal_id": plan_meal.meal_id,
                "recipe_name": meal.recipe_name,
                "description": meal.description,
                "imageUrl": meal.image,
                "macros": {
                    #round to 0 decimal place
                    "caloriesKcal": round(float(plan_meal.calories_kcal), 0) if plan_meal.calories_kcal else 0.0,
                    "proteinG": round(float(plan_meal.protein_g), 0) if plan_meal.protein_g else 0.0,
                    "carbsG": round(float(plan_meal.carbs_g), 0) if plan_meal.carbs_g else 0.0,
                    "fatG": round(float(plan_meal.fat_g), 0) if plan_meal.fat_g else 0.0,
                    "fiberG": round(float(plan_meal.fiber_g), 0) if plan_meal.fiber_g else 0.0
                },
                "preparation": "\n".join(prep_steps) if prep_steps else "",
                "ingredients": ingredients,
                "foods_struct": foods_struct,
                "total_quantity": round(total_quantity, 1),
                "total_quantity_unit": "g"
            }
            return recipe_details

    except SQLAlchemyError as ex:
        raise RepositoryException("Failed to load planned meal recipe details") from ex

