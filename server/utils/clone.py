from typing import Any, Dict

def fast_clone_ingredient(ing: Dict[str, Any]) -> Dict[str, Any]:
    if not ing:
        return {}
    out = ing.copy()
    if "macros" in out and isinstance(out["macros"], dict):
        out["macros"] = out["macros"].copy()
    return out

def fast_clone_food(food: Dict[str, Any]) -> Dict[str, Any]:
    if not food:
        return {}
    out = food.copy()
    if "macros" in out and isinstance(out["macros"], dict):
        out["macros"] = out["macros"].copy()
    if "ingredients_struct" in out and isinstance(out["ingredients_struct"], list):
        out["ingredients_struct"] = [fast_clone_ingredient(ing) for ing in out["ingredients_struct"]]
    return out

def fast_clone_meal(meal: Dict[str, Any]) -> Dict[str, Any]:
    if not meal:
        return {}
    out = meal.copy()
    if "_macros" in out and isinstance(out["_macros"], dict):
        out["_macros"] = out["_macros"].copy()
    if "macros" in out and isinstance(out["macros"], dict):
        out["macros"] = out["macros"].copy()
    if "foods_struct" in out and isinstance(out["foods_struct"], list):
        out["foods_struct"] = [fast_clone_food(f) for f in out["foods_struct"]]
    if "ingredients_struct" in out and isinstance(out["ingredients_struct"], list):
        out["ingredients_struct"] = [fast_clone_ingredient(ing) for ing in out["ingredients_struct"]]
    return out
