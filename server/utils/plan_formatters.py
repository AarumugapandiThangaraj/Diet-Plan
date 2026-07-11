from typing import Dict, Any, List

def format_active_plan(plan_payload: Dict[str, Any], consumed_meal_ids: set = None, meal_lookup: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    if consumed_meal_ids is None:
        consumed_meal_ids = set()
        
    plans_list = plan_payload.get("plans") if "plans" in plan_payload else [plan_payload.get("plan", {})]
    day_ids = plan_payload.get("dayIds", [])
    weeks_data = []
    
    for i in range(0, len(plans_list), 7):
        week_days = plans_list[i:i+7]
        week_num = (i // 7) + 1
        days_data = []
        for j, day_plan in enumerate(week_days):
            day_num = i + j + 1
            p_day_id = day_ids[i+j] if i+j < len(day_ids) else None
            day_meals = []
            day_totals = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
            
            for session, meal in day_plan.items():
                if not isinstance(meal, dict):
                    continue
                macros = meal.get("macros") or {}
                for mk in day_totals.keys():
                    day_totals[mk] += float(macros.get(mk) or 0.0)
                    
                meal_id = str(meal.get("id") or "")
                
                foods = meal.get("foods_struct") or []
                foods_list = []
                for f in foods:
                    foods_list.append({
                        "id": str(f.get("food_instance_id") or f.get("id") or ""),
                        "name": str(f.get("name") or f.get("food_name") or ""),
                        "servingSize": str(f.get("serving_size") or ""),
                        "quantity": float(f.get("quantity") or 1.0),
                        "unit": str(f.get("unit") or "serving")
                    })
                
                # Fallback for time
                scheduled_time = meal.get("scheduled_time") or meal.get("time") or ""
                if not scheduled_time:
                    time_map = {
                        "early_morning": "06:00 AM",
                        "breakfast": "08:30 AM",
                        "mid_morning": "11:00 AM",
                        "lunch": "01:00 PM",
                        "evening": "04:30 PM",
                        "dinner": "08:00 PM",
                        "bedtime": "10:00 PM"
                    }
                    scheduled_time = time_map.get(session, "12:00 PM")
                    
                # Map session names for display
                session_name_map = {
                    "early_morning": "Early Morning",
                    "breakfast": "Breakfast",
                    "mid_morning": "Mid Morning Snack",
                    "lunch": "Lunch",
                    "evening": "Evening Snack",
                    "dinner": "Dinner",
                    "bedtime": "Bedtime"
                }
                display_session = str(meal.get("session") or session)
                if display_session in session_name_map:
                    display_session = session_name_map[display_session]
                    
                day_meals.append({
                    "mealId": meal_id,
                    "name": str(meal.get("name") or meal.get("meal_name") or ""),
                    "image_ID": meal_lookup.get(str(meal.get("Meal_ID") or meal.get("meal_id") or meal_id), {}).get("image_ID", "") or str(meal.get("image_ID") or "") if meal_lookup else str(meal.get("image_ID") or ""),
                    "session": display_session,
                    "scheduledTime": scheduled_time,
                    "macros": {k: float(v) for k, v in macros.items()},
                    "consumed": meal_id in consumed_meal_ids,
                    "foods": foods_list,
                    "ingredients": meal.get("ingredients"),
                    "is_food_swappable": len(foods_list) > 1 if foods_list else (len(meal.get("ingredients", [])) > 1 if isinstance(meal.get("ingredients"), list) else False)
                })
            
            days_data.append({
                "dayNumber": day_num,
                "planDayId": p_day_id,
                "totals": day_totals,
                "meals": day_meals
            })
            
        weeks_data.append({
            "weekNumber": week_num,
            "days": days_data
        })
        
    return weeks_data

def format_draft_plan(plan_payload: Dict[str, Any], meal_lookup: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    plans_list = plan_payload.get("plans") if "plans" in plan_payload else [plan_payload.get("plan", {})]
    totals_by_day = plan_payload.get("totalsByDay", [])
    day_ids = plan_payload.get("dayIds", [])
    
    formatted_days = []
    
    for i, day_plan in enumerate(plans_list):
        formatted_day = {}
        formatted_day["dayNumber"] = i + 1
        
        if i < len(day_ids):
            formatted_day["planDayId"] = day_ids[i]
            
        # Add totals for this specific day explicitly
        if i < len(totals_by_day):
            formatted_day["totals"] = totals_by_day[i]
        else:
            # Fallback calculate totals
            day_totals = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}
            for session, meal in day_plan.items():
                if isinstance(meal, dict):
                    macros = meal.get("macros", {})
                    for mk in day_totals.keys():
                        day_totals[mk] += float(macros.get(mk) or 0.0)
            formatted_day["totals"] = day_totals
            
        # Map sessions explicitly in order
        session_order = ["early_morning", "breakfast", "mid_morning", "lunch", "evening", "dinner", "bedtime"]
        day_meals = []
        for session in session_order:
            meal = day_plan.get(session)
            if meal and isinstance(meal, dict):
                # Ensure the meal object has standard UI fields mapped correctly if needed
                meal["name"] = str(meal.get("name") or meal.get("meal_name") or "")
                
                meal_db_id = str(meal.get("Meal_ID") or meal.get("meal_id") or "")
                img_val = meal_lookup.get(meal_db_id, {}).get("image_ID", "") if meal_lookup and meal_db_id else ""
                if not img_val:
                    img_val = str(meal.get("image_ID") or meal.get("imageUrl") or "")
                meal["image_ID"] = img_val
                meal.pop("imageUrl", None)
                
                # Map session names for display
                session_name_map = {
                    "early_morning": "Early Morning",
                    "breakfast": "Breakfast",
                    "mid_morning": "Mid Morning Snack",
                    "lunch": "Lunch",
                    "evening": "Evening Snack",
                    "dinner": "Dinner",
                    "bedtime": "Bedtime"
                }
                display_session = str(meal.get("session") or session)
                if display_session in session_name_map:
                    display_session = session_name_map[display_session]
                meal["session"] = display_session
                
                # Determine scheduled time
                scheduled_time = meal.get("scheduled_time") or meal.get("time") or ""
                if not scheduled_time:
                    time_map = {
                        "early_morning": "06:00 AM",
                        "breakfast": "08:30 AM",
                        "mid_morning": "11:00 AM",
                        "lunch": "01:00 PM",
                        "evening": "04:30 PM",
                        "dinner": "08:00 PM",
                        "bedtime": "10:00 PM"
                    }
                    scheduled_time = time_map.get(session, "12:00 PM")
                meal["scheduledTime"] = scheduled_time
                
                # Map foods_struct (containing database-scaled quantities) into foods
                foods = meal.get("foods_struct") or []
                foods_list = []
                for f in foods:
                    foods_list.append({
                        "id": str(f.get("food_instance_id") or f.get("id") or ""),
                        "name": str(f.get("name") or f.get("food_name") or ""),
                        "servingSize": str(f.get("serving_size") or ""),
                        "quantity": float(f.get("quantity") or 1.0),
                        "unit": str(f.get("unit") or "serving")
                    })
                
                # Format the meal dictionary to standard layout containing scaled macros
                macros = meal.get("macros") or {}
                meal_formatted = {
                    "mealId": str(meal.get("id") or ""),
                    "name": meal["name"],
                    "image_ID": meal["image_ID"],
                    "session": display_session,
                    "scheduledTime": scheduled_time,
                    "macros": {k: float(v) for k, v in macros.items()},
                    "foods": foods_list,
                    "ingredients": meal.get("ingredients"),
                    "is_food_swappable": len(foods_list) > 1 if foods_list else False
                }
                
                day_meals.append(meal_formatted)
                
        formatted_day["meals"] = day_meals
        formatted_days.append(formatted_day)
        
    weeks_data = []
    current_week = []
    week_num = 1
    
    for day in formatted_days:
        current_week.append(day)
        if len(current_week) == 7:
            weeks_data.append({
                "weekNumber": week_num,
                "days": current_week
            })
            week_num += 1
            current_week = []
            
    if current_week:
        weeks_data.append({
            "weekNumber": week_num,
            "days": current_week
        })
        
    return weeks_data
