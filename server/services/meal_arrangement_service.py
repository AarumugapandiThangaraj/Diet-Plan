from typing import List, Dict, Any

def arrange_meals(selected_meal_ids: List[int], days: int) -> List[int]:
    """
    Arranges selected meals across a given number of days using a round-robin approach.
    Replicates the frontend logic: `list[dayIndex % list.length]`
    """
    if not selected_meal_ids:
        return []
    
    assigned_meals = []
    for day_index in range(days):
        picked = selected_meal_ids[day_index % len(selected_meal_ids)]
        assigned_meals.append(picked)
    
    return assigned_meals

def arrange_plan_sessions(pools_by_time: Dict[str, List[Any]], days: int, meal_times: List[str]) -> Dict[str, List[Any]]:
    """
    Arranges the meal IDs for each requested meal time over the specified number of days.
    """
    assignment_by_time = {}
    for meal_time in meal_times:
        meal_pool = pools_by_time.get(meal_time, [])
        assignment_by_time[meal_time] = arrange_meals(meal_pool, days)
    
    return assignment_by_time
