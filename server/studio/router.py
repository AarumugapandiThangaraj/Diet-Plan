"""
FastAPI Studio Router

Exposes REST API endpoints for the Plan Studio UI, covering daily target calculations, 
meal ranking, plan compilation, and swapping operations (meal/food/ingredient swaps).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    StudioProfile,
    TargetsRequest,
    RankRequest,
    BuildPlanRequest,
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
    DashboardRequest,
    DashboardResponse,
    ConsumeMealRequest,
    ConsumeMealResponse,
    LogHydrationRequest,
    LogHydrationResponse
)
from services.planner_service import (
    fetch_daily_targets_service,
    fetch_ranked_meals_service,
    get_meal_swap_options_service,
    get_food_swap_options_service,
    get_ingredient_swap_options_service,
    apply_food_swap_service,
    apply_ingredient_swap_service,
    save_user_plan_service,
    get_active_user_plan_service,
    strip_plan_payload
)
from config.constants import MEAL_TIME_ORDER, VALID_CUISINES
from repositories.meal_repository import load_master_meals, meal_index_by_id
from services.ranking_service import session_target_macros
from domain.scaling_formulas import ensure_macros, format_nutritive_values, scale_meal_to_targets
from domain.substitutes import suggest_for_ingredients_text
from domain.swap_engine import meal_for_plan_payload

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

@router.post(
    "/targets",
    response_model=DailyTargetsResponse,
    tags=["Planner"],
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
        "      \"age\": 28,\n"
        "      \"gender\": \"male\",\n"
        "      \"heightCm\": 175.0,\n"
        "      \"weightKg\": 75.0,\n"
        "      \"activityLevel\": \"moderate\",\n"
        "      \"goal\": \"skin_repair\",\n"
        "      \"dietType\": \"non_veg\",\n"
        "      \"allergies\": \"peanut,gluten\",\n"
        "      \"cuisineType\": \"south_indian\"\n"
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
    return fetch_daily_targets_service(profile_dict)
    
@router.post(
    "/rank",
    response_model=RankResponse,
    tags=["Nutrition"],
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
        "    \"assignmentByTime\": {\n"
        "      \"breakfast\": [\"meal_1\"],\n"
        "      \"lunch\": [\"meal_3\"],\n"
        "      \"dinner\": [\"meal_5\"]\n"
        "    }\n"
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
async def studio_build_plan(req: BuildPlanRequest):
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
    idx = meal_index_by_id(cuisine)

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
        await save_user_plan_service("00000000-0000-0000-0000-000000000000", days, stripped_payload, profile)
    except Exception as e:
        import logging, traceback
        logging.getLogger("app.studio").error(f"Failed to auto-persist generated plan: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to save plan.")

    return {"success": True, "message": "Plan built successfully."}

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
async def studio_get_active_plan():
    plan = await get_active_user_plan_service("00000000-0000-0000-0000-000000000000")
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found.")
    return plan["plan_payload"]

@router.post(
    "/swap/meal/options",
    response_model=MealSwapOptionsResponse,
    tags=["Swaps"],
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
        "    \"profile\": {\n"
        "      \"age\": 28,\n"
        "      \"gender\": \"male\",\n"
        "      \"heightCm\": 175.0,\n"
        "      \"weightKg\": 75.0,\n"
        "      \"activityLevel\": \"moderate\",\n"
        "      \"goal\": \"skin_repair\",\n"
        "      \"dietType\": \"non_veg\",\n"
        "      \"allergies\": \"\",\n"
        "      \"cuisineType\": \"south_indian\"\n"
        "    },\n"
        "    \"mealTime\": \"lunch\",\n"
        "    \"currentMealId\": \"meal_123\",\n"
        "    \"targetMacros\": {\n"
        "      \"caloriesKcal\": 500.0,\n"
        "      \"proteinG\": 30.0,\n"
        "      \"carbsG\": 60.0,\n"
        "      \"fatG\": 15.0\n"
        "    },\n"
        "    \"excludeMealIds\": [\"meal_123\"],\n"
        "    \"allowedMealIds\": [],\n"
        "    \"topN\": 5\n"
        "  }'\n"
        "```"
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
def studio_swap_meal_options(req: MealSwapOptionsRequest):
    profile = _apply_cuisine(req.profile.model_dump())
    mt = str(req.mealTime or "")
    if mt not in MEAL_TIME_ORDER:
        raise HTTPException(status_code=400, detail="mealTime is invalid.")

    return get_meal_swap_options_service(
        profile=profile,
        meal_time=mt,
        current_meal_id=req.currentMealId,
        target_macros=req.targetMacros,
        exclude_meal_ids=req.excludeMealIds,
        allowed_meal_ids=req.allowedMealIds,
        top_n=req.topN,
        cuisine=profile.get("cuisineType") or "north_indian"
    )

@router.post(
    "/swap/meal/apply",
    response_model=SwapMealApplyResponse,
    tags=["Swaps"],
    summary="Apply Meal Swap and Normalize Macros",
    description=(
        "Standardizes the selected replacement meal payload, ensuring macros are aligned, "
        "calculating formatting strings for display, and applying display scaling attributes.\n\n"
        "### Example cURL Command:\n"
        "```bash\n"
        "curl -X POST http://localhost:8000/api/studio/swap/meal/apply \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d '{\n"
        "    \"meal\": {\n"
        "      \"id\": \"meal_456\",\n"
        "      \"name\": \"Paneer Tikka Salad\",\n"
        "      \"cuisine_type\": \"north_indian\",\n"
        "      \"meal_time\": \"lunch\",\n"
        "      \"macros\": {\n"
        "        \"caloriesKcal\": 420.0,\n"
        "        \"proteinG\": 22.0,\n"
        "        \"carbsG\": 15.0,\n"
        "        \"fatG\": 30.0,\n"
        "        \"fiberG\": 6.0\n"
        "      }\n"
        "    }\n"
        "  }'\n"
        "```"
    ),
    responses={
        200: {
            "description": "Meal swap applied and standardized successfully.",
            "model": SwapMealApplyResponse
        },
        400: {
            "description": "Empty meal data or validation failure.",
            "model": ErrorResponse
        },
        500: {
            "description": "Internal parsing error.",
            "model": ErrorResponse
        }
    }
)
def studio_swap_meal_apply(req: MealSwapApplyRequest):
    meal = dict(req.meal or {})
    if not meal:
        raise HTTPException(status_code=400, detail="Meal payload is required.")

    macros = ensure_macros(meal.get("macros") or meal.get("_macros") or {})
    meal["macros"] = macros
    meal["_macros"] = macros
    if not str(meal.get("nutritive_values") or "").strip():
        meal["nutritive_values"] = format_nutritive_values(macros)

    return {"meal": meal_for_plan_payload(meal)}

@router.post(
    "/swap/food/options",
    response_model=SwapFoodOptionsResponse,
    tags=["Swaps"],
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
def studio_swap_food_options(req: FoodSwapOptionsRequest):
    cuisine = req.meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    return get_food_swap_options_service(meal=req.meal, food_name=req.foodName, top_n=req.topN, cuisine=str(cuisine))

@router.post(
    "/swap/food/apply",
    response_model=SwapMealApplyResponse,
    tags=["Swaps"],
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
        "      \"id\": \"meal_123\",\n"
        "      \"name\": \"Oatmeal with Almonds\",\n"
        "      \"foods\": [\n"
        "        {\"name\": \"Oats\", \"quantity\": 50, \"unit\": \"g\"},\n"
        "        {\"name\": \"Almonds\", \"quantity\": 10, \"unit\": \"g\"}\n"
        "      ]\n"
        "    },\n"
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
def studio_swap_food_apply(req: FoodSwapApplyRequest):
    cuisine = req.meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    meal = apply_food_swap_service(meal=req.meal, option=req.option, cuisine=str(cuisine))
    return {"meal": meal}

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
    cuisine = req.meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    return get_ingredient_swap_options_service(meal=req.meal, ingredient_query=req.ingredientQuery, top_n=req.topN, cuisine=str(cuisine))

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
    cuisine = req.meal.get("cuisine_type") or "north_indian"
    if isinstance(cuisine, list) and len(cuisine) > 0:
        cuisine = cuisine[0]
    meal = apply_ingredient_swap_service(meal=req.meal, option=req.option, cuisine=str(cuisine))
    return {"meal": meal}

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
    "/dashboard/{user_id}",
    response_model=DashboardResponse,
    tags=["Planner"],
    summary="Get Phase 1 Dashboard Summary",
    description="Returns daily targets, health metrics, water goals, and today's scheduled meals with calories remaining.",
)
async def studio_dashboard(user_id: str):
    
    plan = await get_active_user_plan_service(user_id)
    
    if not plan:
        return {
            "activePlan": False,
            "dailyTargets": {},
            "healthMetrics": {},
            "hydration": {},
            "energySummary": {},
            "todayMeals": [],
            "goal": "",
            "activityLevel": "",
            "cuisineType": "",
            "currentDay": 0,
            "totalDays": 0,
        }
    
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
    
    # Fetch hydration consumption log
    from datetime import date
    from repositories.user_water_log_repository import get_water_consumption_log
    
    today_date = date.today()
    water_log = await get_water_consumption_log(user_id, today_date)
    consumed_water_ml = water_log.water_ml if water_log else 0
    target_water_l = targets.get("waterL", 0)
    target_water_ml = target_water_l * 1000
    completion_percentage = int((consumed_water_ml / target_water_ml) * 100) if target_water_ml > 0 else 0
    
    hydration_data = {
        "targetWaterL": target_water_l,
        "consumedWaterMl": consumed_water_ml,
        "completionPercentage": completion_percentage
    }
    
    plan_payload = plan["plan_payload"]
    start_date = plan["start_date"]
    if isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)
        
    day_index = (date.today() - start_date).days
    
    today_meals_dict = {}
    total_days = plan_payload.get("days") or 1
    current_day = 1

    if "plan" in plan_payload:
        today_meals_dict = plan_payload["plan"]
        current_day = 1
        total_days = 1
    elif "plans" in plan_payload and isinstance(plan_payload["plans"], list) and plan_payload["plans"]:
        plans_list = plan_payload["plans"]
        total_days = len(plans_list)
        idx = max(0, min(total_days - 1, day_index))
        if day_index >= total_days or day_index < 0:
            idx = day_index % total_days
        today_meals_dict = plans_list[idx]
        current_day = idx + 1

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
            "name": str(meal.get("meal_name") or ""),
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
    
    return {
        "activePlan": True,
        "dailyTargets": daily_targets_data,
        "healthMetrics": health_metrics_data,
        "hydration": hydration_data,
        "energySummary": energy_summary,
        "todayMeals": today_meals,
        "goal": "",
        "activityLevel": "",
        "cuisineType": "",
        "currentDay": current_day,
        "totalDays": total_days,
    }


@router.post(
    "/dashboard/meals/consume",
    response_model=ConsumeMealResponse,
    tags=["Planner"],
    summary="Toggle Meal Consumption Log",
    description="Records the consumed status of a meal in the database.",
)
async def studio_consume_meal(req: ConsumeMealRequest):
    from datetime import date
    from repositories.user_meal_log_repository import save_meal_consumption_log
    
    try:
        meal_date_parsed = date.fromisoformat(req.mealDate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
        
    log_obj = await save_meal_consumption_log(
        user_identifier=req.userId,
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
    description="UPSERTs the water consumption log (in milliliters) for a user and date.",
)
async def studio_log_hydration(req: LogHydrationRequest):
    from datetime import date
    from repositories.user_water_log_repository import save_water_consumption_log
    
    try:
        log_date_parsed = date.fromisoformat(req.logDate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
        
    # Query active plan to fetch targets (waterL)
    plan = await get_active_user_plan_service(req.userId)
    if plan and "plan_payload" in plan and "targets" in plan["plan_payload"]:
        target_water_l = plan["plan_payload"]["targets"].get("waterL", 2.0)
    else:
        # Fallback target calculation using minimal profile
        profile_dict = {"user_identifier": req.userId}
        targets = fetch_daily_targets_service(profile_dict)
        target_water_l = targets.get("waterL", 2.0)
        
    target_water_ml = target_water_l * 1000
    
    log_obj = await save_water_consumption_log(
        user_identifier=req.userId,
        log_date=log_date_parsed,
        water_ml=req.waterMl
    )
    
    completion_percentage = int((log_obj.water_ml / target_water_ml) * 100) if target_water_ml > 0 else 0
    
    return {
        "success": True,
        "consumedWaterMl": log_obj.water_ml,
        "completionPercentage": completion_percentage
    }

