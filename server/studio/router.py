"""
FastAPI Studio Router

Exposes REST API endpoints for the Plan Studio UI, covering daily target calculations, 
meal ranking, plan compilation, and swapping operations (meal/food/ingredient swaps).
"""

from schemas import CreateDraftResponse

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Depends
import uuid
from sqlalchemy.future import select
from database.session import AsyncSessionLocal
from database.models.plan import DietPlanMeal
from database.models.catalog import MealSession

from schemas import (
    StudioProfile,
    TargetsRequest,
    RankRequest,
    BuildPlanRequest,
    SavePlanRequest,
    SubstitutesRequest,
    MealSwapOptionsRequest,
    MealSwapApplyRequest,
    FoodSwapOptionsRequest,
    FoodSwapApplyRequest,
    IngredientSwapOptionsRequest,
    IngredientSwapApplyRequest,
    StudioMetaResponse,
    DailyTargetsResponse,
    RankResponse,
    BuildPlanResponse,
    MealSwapOptionsResponse,
    SwapMealApplyResponse,
    SwapFoodOptionsResponse,
    SwapIngredientOptionsResponse,
    SubstitutesResponse,
    ErrorResponse,
    ActivePlanResponse,
    DraftPlanResponse,
    DashboardRequest,
    DashboardResponse,
    ConsumeMealRequest,
    ConsumeMealResponse,
    LogHydrationRequest,
    LogHydrationResponse,
    CuisineListResponse,
    CreateDraftRequest,
    DraftPlanResponse,
    PatchPlanRequest,
    ActivatePlanRequest,
    ActivatePlanResponse,
    RecipeDetailResponse,
    RecipeDetailsResponse
)
from services.planner_service import (
    fetch_daily_targets_service,
    fetch_ranked_meals_service,
    get_food_swap_options_service,
    get_ingredient_swap_options_service,
    apply_food_swap_service,
    apply_ingredient_swap_service,
    save_user_plan_service,
    get_draft_user_plan_service,
    update_draft_user_plan_service,
    activate_draft_user_plan_service,
    get_active_user_plan_service,
    strip_plan_payload
)
from services.catalog_service import get_all_cuisines_service
from config.constants import MEAL_TIME_ORDER, VALID_CUISINES
from repositories.meal_repository import load_master_meals, meal_index_by_id
from services.ranking_service import session_target_macros
from services.swap_service import format_nutritive_values, meal_for_plan_payload, get_meal_swap_options_async
from services.meal_arrangement_service import arrange_plan_sessions
from utils.dependencies import get_current_user_id
from domain.scaling_formulas import scale_meal_to_targets, ensure_macros

router = APIRouter(prefix="/api/studio")

def _apply_cuisine(profile_dict: dict) -> dict:
    return profile_dict

def get_loaded_source_path(cuisine: str) -> str:
    return f"[{cuisine}] PostgreSQL Database (Authoritative Ingredient Cache)"

@router.get(
    "/meta",
    response_model=StudioMetaResponse,
    tags=["System"],
    summary="Get Plan Studio Metadata",
    description=(
        "Retrieves configuration parameters, metadata, and support matrices required to initialize "
        "the Plan Studio frontend application. This is a critical endpoint for frontend initialization.\n\n"
        "### Information Returned:\n"
        "- **Meal Times**: Supported meal sessions in chronological order.\n"
        "- **Meals Count**: Total available recipes/meals in the database for the requested cuisine.\n"
        "- **Data Source**: Details on cache/persistence layer source.\n"
        "- **Valid Cuisines**: Full key-value dictionary of supported cuisine options."
    ),
    responses={
        200: {
            "description": "Metadata retrieved successfully.",
            "model": StudioMetaResponse
        },
        500: {
            "description": "Internal server or database error.",
            "model": ErrorResponse
        }
    }
)
def studio_meta(cuisine: str = "north_indian"):
    meals = load_master_meals(cuisine)
    return {
        "mealTimes": MEAL_TIME_ORDER,
        "mealsCount": len(meals),
        "dataSource": get_loaded_source_path(cuisine),
        "validCuisines": VALID_CUISINES,
        "activeCuisine": cuisine,
    }

@router.get(
    "/cuisines",
    response_model=CuisineListResponse,
    tags=["System", "dev"],
    summary="Get All Cuisines",
    description="Retrieves a list of all active cuisines available in the system.",
    responses={
        200: {
            "description": "Cuisine list fetched successfully.",
            "model": CuisineListResponse
        },
        500: {
            "description": "Internal server or database error.",
            "model": ErrorResponse
        }
    }
)
async def get_all_cuisines():
    return await get_all_cuisines_service()

@router.post(
    "/targets",
    response_model=DailyTargetsResponse,
    tags=["Planner","dev"],
    summary="Calculate Daily Calorie & Macro Targets",
    description=(
        "Calculates customized daily energy (calories) and macronutrient (protein, carbs, fat, fiber) targets "
        "as well as target weight, BMI, and water intake requirements based on user demographics and goals.\n\n"
        "### Supported Goal Categories:\n"
        "- `skin_repair`: Focuses on antioxidant-rich micronutrient densities and collagen-boosting targets.\n"
        "- `hair_repair`: Focuses on high-quality proteins and trace mineral targets.\n\n"
        "### Supported Activity Levels:\n"
        "- `sedentary` (multiplier: 1.2)\n"
        "- `light` (multiplier: 1.375)\n"
        "- `moderate` (multiplier: 1.55)\n"
        "- `heavy` (multiplier: 1.725)\n\n"
        "Uses the Mifflin-St Jeor equation for BMR and scales for maintenance calorie levels and specific goals.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/targets \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"profile\": {\n"
        "      \"activityLevel\": \"moderate\",\n"
        "      \"age\": 28,\n"
        "      \"gender\": \"male\",\n"
        "      \"goal\": \"skin_repair\",\n"
        "      \"secondaryGoal\": \"\",\n"
        "      \"heightCm\": 175.0,\n"
        "      \"weightKg\": 75.0\n"
        "    }\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Daily nutrition targets calculated successfully.",
            "model": DailyTargetsResponse
        },
        400: {
            "description": "Validation failure due to invalid demographic or goal parameter values.",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal processing or calculation exception.",
            "model": ErrorResponse
        }
    }
)
def studio_targets(req: TargetsRequest):
    profile_dict = _apply_cuisine(req.profile.model_dump())
    result = fetch_daily_targets_service(profile_dict)
    
    # fill the following data from the result dict
    responses = {
        "idealWeight": result.get("targetWeightKg"),            
        "weightDeltaKg": result.get("weightDeltaKg"),
        "bmi": result.get("bmi"),
        "bmiCategory": result.get("bmiCategory"), 
        "bmr": result.get("bmr"), 
        "tdee": result.get("tdee"), 
        "waterL": result.get("waterL"),
        "waterLMin": result.get("waterLMin"),
        "waterLMax": result.get("waterLMax"),
        "activityLevelNormalized": result.get("activityLevelNormalized"),
        "activityLevel": result.get("activityLevelNormalized") # keeping for backwards compatibility if needed
    }
    return responses
@router.post(
    "/rank",
    response_model=RankResponse,
    tags=["Nutrition","dev"],
    summary="Score and Rank Meals for Requested Sessions",
    description=(
        "Scores and ranks available meal candidates from the database for each requested meal session, "
        "evaluating compatibility with calculated target macros.\n\n"
        "### Scoring Logic:\n"
        "- Compares the candidate meal's protein, carbs, and fat ratio against computed session target macros.\n"
        "- Factors in user dietary preferences (e.g. Vegetarian vs Non-Vegetarian) and filters out allergies.\n"
        "- Returns a sorted list of meals with scores (higher score = better target alignment).\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/rank \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"profile\": {\n"
        "      \"age\": 28,\n"
        "      \"gender\": \"male\",\n"
        "      \"heightCm\": 175.0,\n"
        "      \"weightKg\": 75.0,\n"
        "      \"activityLevel\": \"moderate\",\n"
        "      \"goal\": \"skin_repair\",\n"
        "      \"secondaryGoal\": \"Weight gain\",\n"
        "      \"dietType\": \"non_veg\",\n"
        "      \"allergies\": \"\",\n"
        "      \"cuisineType\": \"south_indian\"\n"
        "    },\n"
        "    \"mealTimes\": [\"breakfast\", \"lunch\", \"dinner\"],\n"
        "    \"limit\": 10\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Meals ranked and scored successfully.",
            "model": RankResponse
        },
        400: {
            "description": "Invalid parameters or empty meal session list provided.",
            "model": ErrorResponse
        },
        500: {
            "description": "Database fetch or processing failure.",
            "model": ErrorResponse
        }
    }
)
def studio_rank(req: RankRequest):
    profile_dict = _apply_cuisine(req.profile.model_dump())
    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")
    return fetch_ranked_meals_service(profile_dict, meal_times, req.limit)

@router.post(
    "/plan/build",
    response_model=dict,
    tags=["Planner"],
    summary="Compile and Build Nutrition Plan",
    description=(
        "Generates a multi-day structured diet plan by assigning selected meals to individual days "
        "and scaling ingredient quantities to precisely match the user's daily macro targets.\n\n"
        "### Planning Constraints:\n"
        "- **Days Range**: Minimum 1 day, maximum 21 days.\n"
        "- **Unique Selections**: A meal cannot be selected in more than one meal session time.\n"
        "- **Selection Limits**: Up to 7 meal choices can be submitted per meal time pool.\n\n"
        "### Meal Session Behavior & Macro Distribution:\n"
        "Daily calorie/macronutrient targets are distributed across session times based on the standard weighting:\n"
        "- `early_morning`: 5% of daily target\n"
        "- `breakfast`: 30% of daily target\n"
        "- `mid_morning`: 10% of daily target\n"
        "- `lunch`: 25% of daily target\n"
        "- `evening`: 10% of daily target\n"
        "- `dinner`: 15% of daily target\n"
        "- `bedtime`: 5% of daily target\n\n"
        "For example, a **3-meal plan** (Breakfast, Lunch, Dinner) assigns target calories based on the relative "
        "weights of those 3 sessions. Ingredients for each day's assigned meals are scaled linearly.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/plan/build \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"profile\": {\n"
        "      \"age\": 28,\n"
        "      \"gender\": \"male\",\n"
        "      \"heightCm\": 175.0,\n"
        "      \"weightKg\": 75.0,\n"
        "      \"activityLevel\": \"moderate\",\n"
        "      \"goal\": \"skin_repair\",\n"
        "      \"secondaryGoal\": \"Weight gain\",\n"
        "      \"dietType\": \"non_veg\",\n"
        "      \"allergies\": \"\",\n"
        "      \"cuisineType\": \"south_indian\"\n"
        "    },\n"
        "    \"days\": 1,\n"
        "    \"mealTimes\": [\"breakfast\", \"lunch\", \"dinner\"],\n"
        "    \"poolsByTime\": {\n"
        "      \"breakfast\": [\"meal_1\", \"meal_2\"],\n"
        "      \"lunch\": [\"meal_3\", \"meal_4\"],\n"
        "      \"dinner\": [\"meal_5\", \"meal_6\"]\n"
        "    },\n"
        
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Plan compiled and scaled successfully."
        },
        400: {
            "description": "Invalid assignment length, duplicate selections, or missing pools.",
            "model": ErrorResponse
        },
        500: {
            "description": "Failed to compile the plan or scale ingredient volumes.",
            "model": ErrorResponse
        }
    }
)
async def studio_build_plan(req: BuildPlanRequest, user_id: str = Depends(get_current_user_id)):
    profile = _apply_cuisine(req.profile.model_dump())
    days = max(1, min(21, int(req.days)))
    targets = fetch_daily_targets_service(profile)

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

    cuisine = profile.get("cuisineType") or "north_indian"
    from repositories.meal_repository import get_meal_index_by_id_async
    idx = await get_meal_index_by_id_async(cuisine)

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

            target_macros = session_target_macros(targets, mt, meal_times)
            scale_info = scale_meal_to_targets(meal, target_macros)
            payload = meal_for_plan_payload(scale_info["scaledMeal"], scale_meta=scale_info)
            plan[mt] = payload

            macros = ensure_macros(payload.get("macros") or {})
            totals["caloriesKcal"] += macros["caloriesKcal"]
            totals["proteinG"] += macros["proteinG"]
            totals["carbsG"] += macros["carbsG"]
            totals["fatG"] += macros["fatG"]
            totals["fiberG"] += macros["fiberG"]

        plans.append(plan)
        totals_by_day.append(totals)
        for k in totals_all.keys():
            totals_all[k] += totals[k]

    res_payload = {
        "days": days,
        "targets": targets,
        "plans": plans,
        "totalsByDay": totals_by_day,
        "totalsAll": totals_all,
        "mealTimes": meal_times,
    } if days > 1 else {
        "days": 1,
        "targets": targets,
        "plan": plans[0] if plans else {},
        "totals": totals_by_day[0] if totals_by_day else None,
        "mealTimes": meal_times,
    }

    stripped_payload = strip_plan_payload(res_payload)

    try:
        await save_user_plan_service(user_id, days, stripped_payload, profile)
    except Exception as e:
        import logging, traceback
        logging.getLogger("app.studio").error(f"Failed to auto-persist generated plan: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to save plan.")

    return {"success": True, "message": "Plan built successfully."}


@router.post(
    "/meal-plans",
    tags=["dev"],
    response_model=CreateDraftResponse,
    status_code=201,
    summary="Create Draft Meal Plan",
    responses={
        201: {"description": "Draft plan created successfully."}
    }
)
async def create_draft_plan(req: CreateDraftRequest, user_id: str = Depends(get_current_user_id)):
    """
    Backend arrangement logic for generating a draft meal plan.
    It takes a pool of selected meal IDs for each meal time and distributes them across the requested days.
    """
    profile = _apply_cuisine(req.profile.model_dump())
    days = max(1, min(21, int(req.days)))
    targets = fetch_daily_targets_service(profile)

    meal_times = [t for t in req.mealTimes if t in MEAL_TIME_ORDER]
    if not meal_times:
        raise HTTPException(status_code=400, detail="mealTimes must include at least one valid meal time")

    pools_by_time = req.poolsByTime or {}

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

    # Use the Backend Meal Arrangement Engine to distribute meals
    assignment_by_time = arrange_plan_sessions(pools_by_time, days, meal_times)

    cuisine = profile.get("cuisineType") or "north_indian"
    from repositories.meal_repository import get_meal_index_by_id_async
    idx = await get_meal_index_by_id_async(cuisine)

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

            target_macros = session_target_macros(targets, mt, meal_times)
            scale_info = scale_meal_to_targets(meal, target_macros)
            payload = meal_for_plan_payload(scale_info["scaledMeal"], scale_meta=scale_info)
            plan[mt] = payload

            macros = ensure_macros(payload.get("macros") or {})
            totals["caloriesKcal"] += macros["caloriesKcal"]
            totals["proteinG"] += macros["proteinG"]
            totals["carbsG"] += macros["carbsG"]
            totals["fatG"] += macros["fatG"]
            totals["fiberG"] += macros["fiberG"]

        plans.append(plan)
        totals_by_day.append(totals)
        for k in totals_all.keys():
            totals_all[k] += totals[k]

    res_payload = {
        "days": days,
        "targets": targets,
        "plans": plans,
        "totalsByDay": totals_by_day,
        "totalsAll": totals_all,
        "mealTimes": meal_times,
    } if days > 1 else {
        "days": 1,
        "targets": targets,
        "plan": plans[0] if plans else {},
        "totals": totals_by_day[0] if totals_by_day else None,
        "mealTimes": meal_times,
    }

    try:
        # Save explicitly as 'draft'
        saved_plan = await save_user_plan_service(user_id, days, res_payload, profile, status='draft')
    except Exception as e:
        import logging, traceback
        logging.getLogger("app.studio").error(f"Failed to persist draft plan: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to save draft plan.")
    
    return {
        "planId": saved_plan["plan_id"],
        "version": saved_plan["version"],
        "status": saved_plan["status"]
    }

    return formatted_data

@router.get(
    "/meal-plans/{plan_id}",
    tags=["dev"],
    response_model=dict,
    status_code=200,
    summary="Get Draft Meal Plan"
)
async def get_draft_plan(plan_id: str, user_id: str = Depends(get_current_user_id)):
    plan_data = await get_draft_user_plan_service(plan_id)
    if not plan_data:
        raise HTTPException(status_code=404, detail="Draft plan not found.")

    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from utils.plan_formatters import format_draft_plan, format_active_plan
    from services.planner_service import get_active_user_plan_service
    
    raw_payload = plan_data.get("plan_payload", {})
    payload = {"weeks": format_draft_plan(raw_payload)}
    payload["targets"] = raw_payload.get("targets", {})
    payload["totalsAll"] = raw_payload.get("totalsAll", {})
    
    payload["planId"] = plan_data.get("plan_id")
    payload["version"] = plan_data.get("version")
    payload["status"] = plan_data.get("status")
    
    active_plan = await get_active_user_plan_service(user_id)
    if active_plan:
        active_payload = active_plan.get("plan_payload", {})
        payload["activePlan"] = {
            "weeks": format_active_plan(active_payload),
            "targets": active_payload.get("targets", {}),
            "totalsAll": active_payload.get("totalsAll", {}),
            "planId": active_plan.get("plan_id"),
            "version": active_plan.get("version"),
            "status": active_plan.get("status")
        }
    else:
        payload["activePlan"] = None

    return payload


@router.patch(
    "/meal-plans/{plan_id}",
    tags=["dev"],
    response_model=dict,
    status_code=200,
    summary="Update Draft Meal Plan"
)
async def update_draft_plan(plan_id: str, req: PatchPlanRequest, user_id: str = Depends(get_current_user_id)):
    from exceptions.repository import RepositoryException
    try:
        updated_plan = await update_draft_user_plan_service(plan_id, user_id, req.version, req.operations)
        
        import sys, os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
        from utils.plan_formatters import format_draft_plan, format_active_plan
        
        raw_payload = updated_plan.get("plan_payload", {})
        status = updated_plan.get("status")
        
        if status == "active":
            payload = {"weeks": format_active_plan(raw_payload)}
        else:
            payload = {"weeks": format_draft_plan(raw_payload)}
            
        payload["targets"] = raw_payload.get("targets", {})
        payload["totalsAll"] = raw_payload.get("totalsAll", {})
        
        payload["planId"] = updated_plan.get("plan_id")
        payload["version"] = updated_plan.get("version")
        payload["status"] = status

        return payload
    except RepositoryException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update plan.")


@router.post(
    "/meal-plans/{plan_id}/activate",
    response_model=ActivatePlanResponse,
    tags=["dev"],
    status_code=200,
    summary="Activate Draft Meal Plan"
)
async def activate_draft_plan(plan_id: str, user_id: str = Depends(get_current_user_id)):
    from exceptions.repository import RepositoryException
    try:
        success = await activate_draft_user_plan_service(plan_id, user_id)
        if success:
            return {"success": True, "status": "active"}
        raise HTTPException(status_code=500, detail="Failed to activate plan.")
    except RepositoryException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to activate plan.")


@router.post(
    "/plan/save",
    response_model=dict,
    tags=["Planner"],
    summary="Save User Diet Plan",
    description="Manually persists the full diet plan state to the database, overwriting the currently active plan. Used to sync the database after swapping foods or meals.",
    responses={
        200: {
            "description": "Plan saved successfully."
        },
        500: {
            "description": "Failed to save plan.",
            "model": ErrorResponse
        }
    }
)
async def studio_save_plan(req: SavePlanRequest, user_id: str = Depends(get_current_user_id)):
    try:
        await save_user_plan_service(user_id, req.days, req.plan_data, req.profile)
    except Exception as e:
        import logging, traceback
        logging.getLogger("app.studio").error(f"Failed to persist plan on /plan/save: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to save plan.")
    return {"success": True, "message": "Plan saved successfully."}

@router.get(
    "/plan/active",
    response_model=dict,
    tags=["Planner"],
    summary="Get Active User Plan",
    description="Fetches the currently active diet plan for the user directly from the database.",
    responses={
        200: {
            "description": "Active plan retrieved successfully."
        },
        404: {
            "description": "No active plan found for the user.",
            "model": ErrorResponse
        }
    }
)
async def studio_get_active_plan(user_id: str = Depends(get_current_user_id)):
    plan = await get_active_user_plan_service(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found.")
    return plan["plan_payload"]

@router.post(
    "/swap/meal/options",
    response_model=MealSwapOptionsResponse,
    tags=["Swaps","dev"],
    summary="Get Alternative Meal Swap Options",
    description=(
        "Retrieves a list of candidate meals from the database that can replace the current meal "
        "in a specific session, matching the target nutritional requirements.\n\n"
        "Calculates options close to either the session macro targets or custom overrides specified in `targetMacros`.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/meal/options \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"planMealId\": \"02627b12-8428-4b13-9be2-4811d4c95f81\"\n"
        "  }'\n"
        "```\n"
        "Alternatively, if not using a database plan, you can manually pass `profile`, `mealTime`, `currentMealId`, and `targetMacros`."
    ),
    responses={
        200: {
            "description": "Swap options retrieved successfully.",
            "model": MealSwapOptionsResponse
        },
        400: {
            "description": "Invalid session time or request parameters.",
            "model": ErrorResponse
        },
        500: {
            "description": "Database or swap engine error.",
            "model": ErrorResponse
        }
    }
)
async def studio_swap_meal_options(req: MealSwapOptionsRequest):
    mt = req.mealTime
    current_meal_id = req.currentMealId
    target_macros = req.targetMacros
    current_meal_name = ""

    if req.planMealId:
        try:
            meal_uuid = uuid.UUID(req.planMealId)
            async with AsyncSessionLocal() as session:
                stmt = select(DietPlanMeal).where(DietPlanMeal.id == meal_uuid)
                meal_obj = (await session.execute(stmt)).scalar_one_or_none()
                if not meal_obj:
                    raise HTTPException(status_code=404, detail=f"Plan meal {req.planMealId} not found")
                
                stmt_sess = select(MealSession).where(MealSession.id == meal_obj.meal_session_id)
                sess_obj = (await session.execute(stmt_sess)).scalar_one_or_none()
                
                current_meal_id = str(meal_obj.meal_id)
                mt = sess_obj.code if sess_obj else req.mealTime
                target_macros = {
                    "caloriesKcal": float(meal_obj.calories_kcal or 0.0),
                    "proteinG": float(meal_obj.protein_g or 0.0),
                    "carbsG": float(meal_obj.carbs_g or 0.0),
                    "fatG": float(meal_obj.fat_g or 0.0),
                    "fiberG": float(meal_obj.fiber_g or 0.0)
                }
                if meal_obj.meal_id:
                    from database.models import Meal
                    meal_name_stmt = select(Meal.recipe_name).where(Meal.id == meal_obj.meal_id)
                    meal_name_res = (await session.execute(meal_name_stmt)).scalar_one_or_none()
                    if meal_name_res:
                        current_meal_name = meal_name_res
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid planMealId format")
    else:
        if current_meal_id:
            try:
                async with AsyncSessionLocal() as session:
                    from database.models import Meal
                    meal_name_stmt = select(Meal.recipe_name).where(Meal.id == int(current_meal_id))
                    meal_name_res = (await session.execute(meal_name_stmt)).scalar_one_or_none()
                    if meal_name_res:
                        current_meal_name = meal_name_res
            except Exception:
                pass

    if not mt or not current_meal_id:
        raise HTTPException(status_code=400, detail="mealTime and currentMealId are required if planMealId is not provided")

    mt = str(mt)
    if mt not in MEAL_TIME_ORDER:
        raise HTTPException(status_code=400, detail="mealTime is invalid.")

    profile = _apply_cuisine(req.profile.model_dump()) if req.profile else {}
    if req.cuisineType:
        profile["cuisineType"] = req.cuisineType

    raw_response = await get_meal_swap_options_async(
        profile=profile,
        meal_time=mt,
        current_meal_id=current_meal_id,
        target_macros=target_macros,
        exclude_meal_ids=req.excludeMealIds,
        allowed_meal_ids=req.allowedMealIds,
        top_n=req.topN
    )

    simplified_options = []
    for opt in raw_response.get("options", []):
        m = opt.get("meal", {})
        simplified_options.append({
            "mealId": opt.get("mealId"),
            "name": m.get("meal_name", ""),
            "macros": m.get("macros", {}),
            "score": opt.get("score", 0.0),
            "scaleFactorRequested": opt.get("scaleFactorRequested", 1.0),
            "scaleFactorApplied": opt.get("scaleFactorApplied", 1.0)
        })

    return {
        "targetMacros": raw_response.get("targetMacros", {}),
        "currentMeal": {
            "mealInstanceId": req.planMealId,
            "mealId": current_meal_id,
            "name": current_meal_name,
            "mealTime": mt,
            "macros": target_macros if target_macros else {}
        },
        "options": simplified_options
    }

@router.patch(
    "/swap/meal/apply",
    response_model=dict,
    tags=["Swaps","dev"],
    summary="Apply Meal Swap and Normalize Macros",
    description=(
        "Applies the selected meal swap to the database, overwriting the old meal instance's macros and foods with the newly selected option.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X PATCH http://localhost:8000/api/studio/swap/meal/apply \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"planMealId\": \"02627b12-8428-4b13-9be2-4811d4c95f81\",\n"
        "    \"newMealId\": \"201\",\n"
        "    \"cuisineType\": \"south_indian\",\n"
        "    \"macros\": {\n"
        "      \"caloriesKcal\": 320.0,\n"
        "      \"proteinG\": 7.5,\n"
        "      \"carbsG\": 53.5,\n"
        "      \"fatG\": 8.7,\n"
        "      \"fiberG\": 3.6\n"
        "    },\n"
        "    \"scaleFactorApplied\": 1.0\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Meal swap applied to database successfully."
        },
        400: {
            "description": "Validation failure.",
            "model": ErrorResponse
        },
        500: {
            "description": "Database or parsing error.",
            "model": ErrorResponse
        }
    }
)
async def studio_swap_meal_apply(req: MealSwapApplyRequest):
    from repositories.draft_plan_repository import apply_meal_swap_to_db
    from exceptions.repository import RepositoryException
    
    try:
        success = await apply_meal_swap_to_db(
            plan_meal_id=req.planMealId,
            new_meal_id=req.newMealId,
            cuisine_type=req.cuisineType,
            macros=req.macros,
            scale_factor=req.scaleFactorApplied
        )
        return {"success": success}
    except RepositoryException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import logging
        logging.error(f"Error applying meal swap: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error applying swap.")

@router.post(
    "/swap/food/options",
    response_model=SwapFoodOptionsResponse,
    tags=["Swaps",'dev'],
    summary="Get Food Item Swap Options",
    description=(
        "Fetches alternative, single-food substitutes within a meal. E.g. replacing 'Almonds' with 'Walnuts' "
        "and calculating the exact quantity conversion ratio to match nutritional profiles.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/food/options \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"meal\": {\n"
        "      \"id\": \"meal_123\",\n"
        "      \"name\": \"Oatmeal with Almonds\",\n"
        "      \"cuisine_type\": \"continental\",\n"
        "      \"foods\": [\n"
        "        {\"name\": \"Oats\", \"quantity\": 50, \"unit\": \"g\"},\n"
        "        {\"name\": \"Almonds\", \"quantity\": 10, \"unit\": \"g\"}\n"
        "      ]\n"
        "    },\n"
        "    \"foodName\": \"Almonds\",\n"
        "    \"topN\": 5\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Food substitute options compiled successfully.",
            "model": SwapFoodOptionsResponse
        },
        500: {
            "description": "Database read or matching index error.",
            "model": ErrorResponse
        }
    }
)
async def studio_swap_food_options(req: FoodSwapOptionsRequest):
    meal = req.meal.model_dump(by_alias=True) if hasattr(req.meal, "model_dump") else dict(req.meal or {})
    cuisine = meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
        
    from services.swap_service import get_food_swap_options_async
    return await get_food_swap_options_async(meal=meal, food_name=req.foodName, top_n=req.topN, cuisine=str(cuisine))

@router.post(
    "/swap/food/apply",
    response_model=SwapMealApplyResponse,
    tags=["Swaps","dev"],
    summary="Apply Food Item Swap to Meal",
    description=(
        "Modifies the meal payload by replacing the selected food item with its swap option, "
        "updating ingredients quantities, and recalculating overall meal macros.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/food/apply \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"meal\": {\n"
        "      \"id\": \"e2343b67-a021-4f11-92b1-5e8f8103c819\",\n"
        "      \"name\": \"Oatmeal with Almonds\",\n"
        "      \"foods_struct\": [\n"
        "        {\"name\": \"Oats\", \"quantity\": 50, \"unit\": \"g\", \"food_instance_id\": \"a9043b67-a021-4f11-92b1-5e8f8103c822\"},\n"
        "        {\"name\": \"Almonds\", \"quantity\": 10, \"unit\": \"g\", \"food_instance_id\": \"b7043b67-c011-4f21-93a1-2e8f8103d111\"}\n"
        "      ]\n"
        "    },\n"
        "    \"planId\": \"3b351669-8451-490a-9e98-583d40cba2ed\",\n"
        "    \"version\": 1,\n"
        "    \"option\": {\n"
        "      \"source_food\": \"Almonds\",\n"
        "      \"target_food\": \"Walnuts\",\n"
        "      \"ratio\": 1.2,\n"
        "      \"target_macros\": {\n"
        "        \"calories\": 654,\n"
        "        \"protein\": 15.2,\n"
        "        \"carbs\": 13.7,\n"
        "        \"fat\": 65.2\n"
        "      }\n"
        "    }\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Food swap applied and meal updated successfully.",
            "model": SwapMealApplyResponse
        },
        500: {
            "description": "Failed to apply swap parameters to recipe.",
            "model": ErrorResponse
        }
    }
)
async def studio_swap_food_apply(req: FoodSwapApplyRequest, user_id: str = Depends(get_current_user_id)):
    meal_dict = req.meal.model_dump(by_alias=True) if hasattr(req.meal, "model_dump") else dict(req.meal or {})
    cuisine = meal_dict.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
        
    meal = apply_food_swap_service(meal=meal_dict, option=req.option, cuisine=str(cuisine))
    
    if req.planId and req.version is not None:
        from schemas import PatchOperation
        from services.planner_service import update_draft_user_plan_service
        
        foods = meal_dict.get("foods_struct") or meal_dict.get("foods") or []
        food_instance_ids = [str(f.get("food_instance_id")) for f in foods if f.get("food_instance_id")]
        
        op = PatchOperation(
            type="food_swap",
            mealInstanceId=str(meal_dict.get("id")),
            customMealPayload=meal,
            foodInstanceIds=food_instance_ids
        )
        
        try:
            await update_draft_user_plan_service(req.planId, user_id, req.version, [op])
        except Exception as e:
            import logging
            logging.getLogger("app.studio").error(f"Failed to persist food swap to DB: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to persist food swap to DB: {str(e)}")
            
    return {
        "success": True,
        "data": {
            "code": "UPDATED",
            "success": True,
            "status": 200,
            "message": "The meal swap has been applied successfully."
        }
    }

@router.post(
    "/swap/ingredient/options",
    response_model=SwapIngredientOptionsResponse,
    tags=["Swaps"],
    summary="Get Ingredient Swap Options",
    description=(
        "Looks up sub-ingredient substitutions (e.g. Olive Oil for Mustard Oil) "
        "and lists options with scaling metrics.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/ingredient/options \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"meal\": {\n"
        "      \"id\": \"meal_789\",\n"
        "      \"name\": \"Chicken Curry\",\n"
        "      \"ingredients\": \"Chicken breast, Onion, Tomato, Mustard oil\"\n"
        "    },\n"
        "    \"ingredientQuery\": \"Mustard oil\",\n"
        "    \"topN\": 5\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Ingredient options fetched successfully.",
            "model": SwapIngredientOptionsResponse
        },
        500: {
            "description": "Internal database exception.",
            "model": ErrorResponse
        }
    }
)
def studio_swap_ingredient_options(req: IngredientSwapOptionsRequest):
    meal = req.meal.model_dump(by_alias=True) if hasattr(req.meal, "model_dump") else dict(req.meal or {})
    cuisine = meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    return get_ingredient_swap_options_service(meal=meal, ingredient_query=req.ingredientQuery, top_n=req.topN, cuisine=str(cuisine))

@router.post(
    "/swap/ingredient/apply",
    response_model=SwapMealApplyResponse,
    tags=["Swaps"],
    summary="Apply Ingredient Swap to Meal",
    description=(
        "Swaps out the target ingredient list with the selected option in the meal recipe.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/ingredient/apply \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"meal\": {\n"
        "      \"id\": \"meal_789\",\n"
        "      \"name\": \"Chicken Curry\",\n"
        "      \"ingredients\": \"Chicken breast, Onion, Tomato, Mustard oil\"\n"
        "    },\n"
        "    \"option\": {\n"
        "      \"source_ingredient\": \"Mustard oil\",\n"
        "      \"target_ingredient\": \"Olive oil\",\n"
        "      \"ratio\": 1.0\n"
        "    }\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Ingredient swap applied successfully.",
            "model": SwapMealApplyResponse
        },
        500: {
            "description": "Failed to update recipe payload.",
            "model": ErrorResponse
        }
    }
)
def studio_swap_ingredient_apply(req: IngredientSwapApplyRequest):
    meal = req.meal.model_dump(by_alias=True) if hasattr(req.meal, "model_dump") else dict(req.meal or {})
    cuisine = meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    meal_out = apply_ingredient_swap_service(meal=meal, option=req.option, cuisine=str(cuisine))
    return {"meal": meal_out}

@router.post(
    "/substitutes/from-ingredients",
    response_model=SubstitutesResponse,
    tags=["Substitutions"],
    summary="Get General Ingredient Substitutes",
    description=(
        "Finds healthy and culinary substitutes for a list of query ingredients "
        "using database mappings and nutritional indexing. Does not require a meal context.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/substitutes/from-ingredients \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"ingredients\": \"milk, paneer\"\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Ingredient substitutes retrieved successfully.",
            "model": SubstitutesResponse
        },
        500: {
            "description": "Failed to process substitutes search.",
            "model": ErrorResponse
        }
    }
)
def studio_substitutes(req: SubstitutesRequest):
    return suggest_for_ingredients_text(req.ingredients)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    tags=["Planner"],
    summary="Get Phase 1 Dashboard Summary",
    description="Returns daily targets, health metrics, water goals, and today's scheduled meals with calories remaining.",
)
async def studio_dashboard(user_id: str = Depends(get_current_user_id)):
    from services.planner_service import get_latest_user_plan_service
    plan = await get_latest_user_plan_service(user_id)
    
    if not plan:
        return {
            "activePlan": False,
            "dailyTargets": {
                "caloriesKcal": 0,
                "proteinG": 0,
                "carbsG": 0,
                "fatG": 0,
                "fiberG": 0,
            },
            "healthMetrics": {
                "bmi": 0.0,
                "bmiCategory": "",
                "targetWeightKg": 0.0,
                "weightKg": 0.0,
                "weightDeltaKg": 0.0,
            },
            "hydration": {
                "targetWaterL": 0.0,
                "consumedWaterMl": 0,
                "completionPercentage": 0,
            },
            "energySummary": {
                "targetCalories": 0,
                "consumedCalories": 0,
                "remainingCalories": 0,
            },
            "todayMeals": [],
            "weeks": [],
            "goal": "",
            "activityLevel": "",
            "cuisineType": "",
            "currentDay": 0,
            "totalDays": 0,
        }
    
    plan_status = plan.get("status", "active")
    plan_id = plan.get("plan_id")
    plan_payload = plan["plan_payload"]
    targets = plan_payload.get("targets", {})
    
    daily_targets_data = {
        "caloriesKcal": targets.get("dailyCalories", 0),
        "proteinG": targets.get("proteinG", 0),
        "carbsG": targets.get("carbsG", 0),
        "fatG": targets.get("fatG", 0),
        "fiberG": targets.get("fiberG", 0),
    }
    
    health_metrics_data = {
        "bmi": targets.get("bmi", 0),
        "bmiCategory": targets.get("bmiCategory", ""),
        "targetWeightKg": 0, # Note: if UI strictly requires these, we can add them to db later
        "weightKg": 0,
        "weightDeltaKg": 0,
    }
    
    from datetime import date
    today_date = date.today()
    
    start_date = plan["start_date"]
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
        
    day_index = (today_date - start_date).days
    
    today_meals_dict = {}
    total_days = plan_payload.get("days") or 1
    current_day = 1
    plan_day_id = None
    
    if "plan" in plan_payload:
        today_meals_dict = plan_payload["plan"]
        current_day = 1
        total_days = 1
        if "dayIds" in plan_payload and plan_payload["dayIds"]:
            plan_day_id = plan_payload["dayIds"][0]
    elif "plans" in plan_payload and isinstance(plan_payload["plans"], list) and plan_payload["plans"]:
        plans_list = plan_payload["plans"]
        total_days = len(plans_list)
        idx = max(0, min(total_days - 1, day_index))
        if day_index >= total_days or day_index < 0:
            idx = day_index % total_days
        today_meals_dict = plans_list[idx]
        current_day = idx + 1
        if "dayIds" in plan_payload and idx < len(plan_payload["dayIds"]):
            plan_day_id = plan_payload["dayIds"][idx]

    # Fetch hydration consumption log
    from repositories.user_water_log_repository import get_water_consumption_log
    
    consumed_water_ml = 0
    if plan_day_id:
        water_log = await get_water_consumption_log(user_id, plan_day_id)
        consumed_water_ml = water_log.water_ml if water_log else 0
        
    target_water_l = targets.get("waterL", 0)
    target_water_ml = target_water_l * 1000
    completion_percentage = int((consumed_water_ml / target_water_ml) * 100) if target_water_ml > 0 else 0
    
    hydration_data = {
        "targetWaterL": target_water_l,
        "consumedWaterMl": consumed_water_ml,
        "completionPercentage": completion_percentage
    }

    # Fetch meal consumption logs for the user on today's date
    from repositories.user_meal_log_repository import get_meal_consumption_logs
    logs = await get_meal_consumption_logs(user_id, today_date)
    consumed_meal_ids = {log.meal_id for log in logs if log.consumed}
        
    today_meals = []
    consumed_calories = 0
    
    for session, meal in today_meals_dict.items():
        if not isinstance(meal, dict):
            continue
        
        macros = meal.get("macros") or {}
        calories = int(macros.get("caloriesKcal") or 0)
        meal_id = str(meal.get("Meal_ID") or "")
        
        is_consumed = meal_id in consumed_meal_ids
        if is_consumed:
            consumed_calories += calories
        
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
            
        today_meals.append({
            "mealId": meal_id,
            "name": str(meal.get("name") or meal.get("meal_name") or ""),
            "imageUrl": str(meal.get("image_ID") or ""),
            "session": session,
            "scheduledTime": scheduled_time,
            "macros": {k: float(v) for k, v in macros.items()},
            "consumed": is_consumed
        })
        
    target_calories = int(targets.get("dailyCalories", 0))
    remaining_calories = max(0, target_calories - consumed_calories)
    
    energy_summary = {
        "targetCalories": target_calories,
        "consumedCalories": consumed_calories,
        "remainingCalories": remaining_calories
    }
    
    # Construct weeks array using the new formatter
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from utils.plan_formatters import format_active_plan
    
    weeks_data = format_active_plan(plan_payload, consumed_meal_ids)
    
    return {
        "activePlan": True if plan_status == 'active' else False,
        "status": plan_status,
        "planId": plan_id,
        "version": plan.get("version", 1),
        "dailyTargets": daily_targets_data,
        "healthMetrics": health_metrics_data,
        "hydration": hydration_data,
        "energySummary": energy_summary,
        "todayMeals": today_meals,
        "weeks": weeks_data,
        "goal": "",
        "activityLevel": "",
        "cuisineType": "",
        "currentDay": current_day,
        "totalDays": total_days,
        "planDayId": plan_day_id,
    }


@router.post(
    "/dashboard/meals/consume",
    response_model=ConsumeMealResponse,
    tags=["Planner"],
    summary="Toggle Meal Consumption Log",
    description="Records the consumed status of a meal in the database.",
)
async def studio_consume_meal(req: ConsumeMealRequest, user_id: str = Depends(get_current_user_id)):
    from datetime import date
    from repositories.user_meal_log_repository import save_meal_consumption_log
    
    try:
        meal_date_parsed = date.fromisoformat(req.mealDate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
        
    log_obj = await save_meal_consumption_log(
        user_identifier=user_id,
        meal_id=req.mealId,
        meal_date=meal_date_parsed,
        consumed=req.consumed
    )
    return {
        "success": True,
        "consumed": log_obj.consumed
    }


@router.post(
    "/hydration",
    response_model=LogHydrationResponse,
    tags=["Planner"],
    summary="Log or Update Today's Water Consumption",
    description="UPSERTs the water consumption log (in milliliters) for a user and diet plan day.",
)
async def studio_log_hydration(req: LogHydrationRequest, user_id: str = Depends(get_current_user_id)):
    from repositories.user_water_log_repository import save_water_consumption_log
    
    # Query active plan to fetch targets (waterL)
    plan = await get_active_user_plan_service(user_id)
    if plan and "plan_payload" in plan and "targets" in plan["plan_payload"]:
        target_water_l = plan["plan_payload"]["targets"].get("waterL", 2.0)
    else:
        # Fallback target calculation using minimal profile
        profile_dict = {"user_identifier": user_id}
        targets = fetch_daily_targets_service(profile_dict)
        target_water_l = targets.get("waterL", 2.0)
        
    target_water_ml = target_water_l * 1000
    
    log_obj = await save_water_consumption_log(
        user_identifier=user_id,
        plan_day_id=req.planDayId,
        water_ml=req.waterMl
    )
    
    completion_percentage = int((log_obj.water_ml / target_water_ml) * 100) if target_water_ml > 0 else 0
    
    return {
        "success": True,
        "consumedWaterMl": log_obj.water_ml,
        "completionPercentage": completion_percentage
    }

@router.get(
    "/plan/latest",
    response_model=Union[ActivePlanResponse, DraftPlanResponse, dict],
    tags=["Diet Plan - User"],
    summary="Get Latest Diet Plan (Active or Draft)",
    description="Retrieves the most recent plan for the current user, whether it is active or a draft."
)
async def studio_get_latest_plan(user_id: str = Depends(get_current_user_id)):
    from services.planner_service import get_latest_user_plan_service
    plan = await get_latest_user_plan_service(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No plan found.")
    payload = plan["plan_payload"]
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from utils.plan_formatters import format_active_plan, format_draft_plan
    
    if plan["status"] == "active":
        formatted_data = {"weeks": format_active_plan(payload)}
    else:
        formatted_data = {"weeks": format_draft_plan(payload)}
        
    # Retain top-level targets and summary if needed
    formatted_data["targets"] = payload.get("targets", {})
    formatted_data["totalsAll"] = payload.get("totalsAll", {})
    
    formatted_data["status"] = plan["status"]
    formatted_data["planId"] = plan["plan_id"]
    formatted_data["version"] = plan["version"]
    
    return formatted_data

# @router.get(
#     "/meal-plans/meals/{mealInstanceId}",
#     response_model=RecipeDetailResponse,
#     tags=["Diet Plan - User"],
#     summary="Get Meal Details for Recipe View",
#     description="Retrieves all information required for the Recipe Detail screen for a specific meal instance."
# )
# async def studio_get_meal_details(mealInstanceId: str, user_id: str = Depends(get_current_user_id)):
#     from repositories.user_plan_repository import get_meal_instance_details
#     meal_details = await get_meal_instance_details(mealInstanceId, user_id)
    
#     if not meal_details:
#         raise HTTPException(status_code=404, detail="Meal instance not found")
        
#     if "error" in meal_details and meal_details["error"] == "forbidden":
#         raise HTTPException(status_code=403, detail="Forbidden")
        
#     return meal_details

from schemas import UserHealthProfileResponse, CreateHealthProfileRequest

@router.get(
    "/health-profile/latest",

    response_model=UserHealthProfileResponse,
    tags=["User","dev"],
    summary="Get Latest Health Profile",
    description="Retrieves the most recent health profile for the current user."
)
async def get_latest_health_profile(user_id: str = Depends(get_current_user_id)):
    from database.models.user import UserHealthProfile
    async with AsyncSessionLocal() as session:
        stmt = select(UserHealthProfile).where(
            UserHealthProfile.user_id == uuid.UUID(user_id),
            UserHealthProfile.is_latest == True
        )
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()
        
        if not profile:
            stmt_fallback = select(UserHealthProfile).where(
                UserHealthProfile.user_id == uuid.UUID(user_id)
            ).order_by(UserHealthProfile.created_at.desc()).limit(1)
            result_fallback = await session.execute(stmt_fallback)
            profile = result_fallback.scalar_one_or_none()
            
        if not profile:
            raise HTTPException(status_code=404, detail="Health profile not found.")
            
        profile_dict = {
            "target_weight_kg": float(profile.target_weight_kg) if profile.target_weight_kg else None,
            "bmi": float(profile.bmi) if profile.bmi else None,
            "bmi_category": profile.bmi_category,
            "bmr_kcal": profile.bmr_kcal,
            "tdee_kcal": profile.tdee_kcal,
            "target_water_l": float(profile.target_water_l) if profile.target_water_l else None,
            "is_latest": profile.is_latest
        }
        return profile_dict

@router.post(
    "/health-profile",
    response_model=UserHealthProfileResponse,
    tags=["User", "dev"],
    summary="Create New Health Profile",
    description="Creates a new health profile for the user based on raw demographic data. Calculates BMR, TDEE, and targets, then saves it as the latest profile."
)
async def create_new_health_profile(profile: CreateHealthProfileRequest, user_id: str = Depends(get_current_user_id)):
    from database.models.user import UserHealthProfile
    from sqlalchemy import update
    
    profile_dict = profile.model_dump()
    # Add defaults required by the planner formulas
    profile_dict["goal"] = "skin_repair" 
    
    targets = fetch_daily_targets_service(profile_dict)
    
    def _int(v): return int(float(v)) if v is not None and str(v).strip() else None
    def _float(v): return float(v) if v is not None and str(v).strip() else None
    
    uid = uuid.UUID(user_id)
    
    activity_mapping = {
        "sedentary": "sedentary",
        "light": "lightly_active",
        "moderate": "moderately_active",
        "heavy": "very_active"
    }
    act_level = profile_dict.get("activityLevel")
    mapped_activity = activity_mapping.get(act_level, act_level)
    
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(UserHealthProfile).where(UserHealthProfile.user_id == uid).values(is_latest=False)
        )
        
        uhp = UserHealthProfile(
            user_id=uid,
            age=_int(profile_dict.get("age")),
            gender=profile_dict.get("gender"),
            height_cm=_float(profile_dict.get("heightCm")),
            weight_kg=_float(profile_dict.get("weightKg")),
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
        await session.commit()
        await session.refresh(uhp)
        
        profile_res = {
            "target_weight_kg": float(uhp.target_weight_kg) if uhp.target_weight_kg else None,
            "bmi": float(uhp.bmi) if uhp.bmi else None,
            "bmi_category": uhp.bmi_category,
            "bmr_kcal": uhp.bmr_kcal,
            "tdee_kcal": uhp.tdee_kcal,
            "target_water_l": float(uhp.target_water_l) if uhp.target_water_l else None,
            "is_latest": uhp.is_latest
        }
        return profile_res


@router.get(
    "/meal-plans/meal/{mealInstanceId}",
    response_model=RecipeDetailsResponse,
    tags=["Recipes","dev"],
    summary="Get Recipe Details for Recipe View UI",
    description="Retrieves the recipe details, including recipe_name, description, macros, and component foods structured with specific ingredients and preparation instructions."
)
async def studio_get_recipe_details(mealInstanceId: str):
    from schemas import RecipeDetailsResponse
    from services.planner_service import get_recipe_details_service
    recipe = await get_recipe_details_service(mealInstanceId)
    if not recipe:
        raise HTTPException(status_code=404, detail="Planned meal or recipe not found.")
    is_food_swappable = len(recipe["foods_struct"]) > 1
    return {
        "mealInstanceId": recipe["mealInstanceId"],
        "meal_id": recipe["meal_id"],
        "is_food_swappable": is_food_swappable,
        "recipe_name": recipe["recipe_name"],
        "description": recipe["description"],
        "imageUrl": recipe["imageUrl"],
        "macros": recipe["macros"],
        "preparation": recipe["preparation"],
        "ingredients": recipe["ingredients"],
        "foods_struct": recipe["foods_struct"]
    }
