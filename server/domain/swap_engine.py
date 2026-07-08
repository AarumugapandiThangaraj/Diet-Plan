from typing import Any, Dict

def _ratio(a: str, b: str) -> float:
    a_str = str(a or "").lower().strip()
    b_str = str(b or "").lower().strip()
    if not a_str or not b_str:
        return 0.0
    if a_str == b_str:
        return 1.0
    
    a_set = set(a_str.split())
    b_set = set(b_str.split())
    if not a_set or not b_set:
        return 0.0
        
    intersect = a_set.intersection(b_set)
    if not intersect:
        if a_str in b_str or b_str in a_str:
            return 0.5
        return 0.0
    return len(intersect) / len(a_set.union(b_set))

def _macro_error(actual: Dict[str, Any], target: Dict[str, Any]) -> float:
    def safe_float(v):
        try: return float(v)
        except: return 0.0
        
    a_cal = safe_float(actual.get("caloriesKcal", 0))
    t_cal = safe_float(target.get("caloriesKcal", 0))
    
    if t_cal <= 0:
        return 0.0 if a_cal <= 0 else 1.0
    return abs(a_cal - t_cal) / t_cal
