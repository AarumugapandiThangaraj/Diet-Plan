from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List

from .meals import MEAL_TIME_ORDER, meal_index_by_id, load_master_meals, rank_meals_for_meal_time
from .nutrition import calculate_daily_targets
from .substitutes import suggest_for_ingredients_text

router = APIRouter(prefix="/api/studio", tags=["diet-plan-studio"])


class StudioProfile(BaseModel):
    age: Any = "30"
    gender: Any = "female"
    heightCm: Any = "165"
    weightKg: Any = "60"
    activityLevel: Any = "sedentary"
    goal: Any = "skin_repair"
    dietType: Any = "non_veg"
    allergies: Any = ""


class TargetsRequest(BaseModel):
    profile: StudioProfile


class RankRequest(BaseModel):
    profile: StudioProfile
    mealTimes: List[str] = Field(default_factory=list)
    limit: int = 180


class BuildPlanRequest(BaseModel):
    profile: StudioProfile
    days: int = Field(7, ge=1, le=21)
    mealTimes: List[str] = Field(default_factory=list)
    poolsByTime: Dict[str, List[str]] = Field(default_factory=dict)
    assignmentByTime: Dict[str, List[str]] = Field(default_factory=dict)


class SubstitutesRequest(BaseModel):
    ingredients: str = ""


@router.get("/meta")
def studio_meta():
    meals = load_master_meals()
    return {"mealTimes": MEAL_TIME_ORDER, "mealsCount": len(meals)}


@router.post("/targets")
def studio_targets(req: TargetsRequest):
    return calculate_daily_targets(req.profile.model_dump())


@router.post("/rank")
def studio_rank(req: RankRequest):
    profile = req.profile.model_dump()
    targets = calculate_daily_targets(profile)

    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")

    ranked_by_time: Dict[str, Any] = {}
    for mt in meal_times:
        ranked_by_time[mt] = rank_meals_for_meal_time(profile=profile, meal_time=mt, targets=targets, limit=req.limit)[
            "ranked"
        ]

    return {"targets": targets, "rankedByTime": ranked_by_time}


@router.post("/plan/build")
def studio_build_plan(req: BuildPlanRequest):
    profile = req.profile.model_dump()
    days = max(1, min(21, int(req.days)))
    targets = calculate_daily_targets(profile)

    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")

    pools_by_time = req.poolsByTime or {}
    assignment_by_time = req.assignmentByTime or {}

    all_ids: set[str] = set()
    for mt in meal_times:
        ids = [str(x) for x in (pools_by_time.get(mt) or []) if str(x)]
        if not ids:
            raise HTTPException(status_code=400, detail=f"Please select at least 1 meal for {mt}.")
        if len(ids) > 7:
            raise HTTPException(status_code=400, detail=f"You can select up to 7 meals for {mt}.")
        for mid in ids:
            if mid in all_ids:
                raise HTTPException(
                    status_code=400,
                    detail="A meal was selected in more than one meal time. Please ensure selections are unique.",
                )
            all_ids.add(mid)

    idx = meal_index_by_id()

    plans: List[Dict[str, Any]] = []
    totals_by_day: List[Dict[str, float]] = []
    totals_all = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}

    for day_index in range(days):
        plan: Dict[str, Any] = {}
        totals = {"caloriesKcal": 0.0, "proteinG": 0.0, "carbsG": 0.0, "fatG": 0.0, "fiberG": 0.0}

        for mt in meal_times:
            assigned = assignment_by_time.get(mt) or []
            meal_id = str(assigned[day_index]) if day_index < len(assigned) else ""
            if not meal_id:
                continue

            meal = idx.get(meal_id)
            if not meal:
                continue

            macros = meal.get("_macros") or {}
            totals["caloriesKcal"] += float(macros.get("caloriesKcal", 0.0) or 0.0)
            totals["proteinG"] += float(macros.get("proteinG", 0.0) or 0.0)
            totals["carbsG"] += float(macros.get("carbsG", 0.0) or 0.0)
            totals["fatG"] += float(macros.get("fatG", 0.0) or 0.0)
            totals["fiberG"] += float(macros.get("fiberG", 0.0) or 0.0)

            plan[mt] = {
                "Meal_ID": meal.get("Meal_ID"),
                "meal_name": meal.get("meal_name"),
                "time": meal.get("time") or "",
                "serving_size": meal.get("serving_size") or "",
                "ingredients": meal.get("ingredients") or "",
                "method": meal.get("method") or "",
                "caution": meal.get("caution") or "",
                "nutritive_values": meal.get("nutritive_values") or "",
                "macros": macros,
            }

        plans.append(plan)
        totals_by_day.append(totals)
        for k in totals_all.keys():
            totals_all[k] += totals[k]

    if days == 1:
        return {
            "days": 1,
            "targets": targets,
            "plan": plans[0] if plans else {},
            "totals": totals_by_day[0] if totals_by_day else None,
            "mealTimes": meal_times,
        }

    return {
        "days": days,
        "targets": targets,
        "plans": plans,
        "totalsByDay": totals_by_day,
        "totalsAll": totals_all,
        "mealTimes": meal_times,
    }


@router.post("/substitutes/from-ingredients")
def studio_substitutes(req: SubstitutesRequest):
    return suggest_for_ingredients_text(req.ingredients)
