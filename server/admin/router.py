"""
FastAPI Admin Router for Data Entry

Exposes REST API endpoints for CRUD operations on:
- Cuisines
- Meal Sessions
- Master Ingredients
- Foods
- Meals
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from database.session import AsyncSessionLocal
from exceptions.base import AppException
from admin.schemas import (
    CuisineCreate, CuisineUpdate, CuisineResponse, CuisineListResponse,
    MealSessionCreate, MealSessionUpdate, MealSessionResponse, MealSessionListResponse,
    MasterIngredientCreate, MasterIngredientUpdate, MasterIngredientResponse, MasterIngredientListResponse,
    FoodCreate, FoodUpdate, FoodResponse, FoodListResponse,
    MealCreate, MealUpdate, MealResponse, MealListResponse,
    FoodRoleCreate, FoodRoleUpdate, FoodRoleResponse, FoodRoleListResponse,
    PrimaryGoalCreate, PrimaryGoalUpdate, PrimaryGoalResponse, PrimaryGoalListResponse,
    SecondaryGoalCreate, SecondaryGoalUpdate, SecondaryGoalResponse, SecondaryGoalListResponse,
)
from admin.services import (
    CuisineService, MealSessionService, MasterIngredientService, FoodService, MealService,
    FoodRoleService, PrimaryGoalService, SecondaryGoalService
)

router = APIRouter(prefix="/api/admin", tags=["Admin Data Entry"])


# ============================================================================
# CUISINES
# ============================================================================

@router.get(
    "/cuisines",
    response_model=CuisineListResponse,
    summary="List All Cuisines",
    description="Retrieve all cuisines with optional pagination."
)
async def list_cuisines(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    async with AsyncSessionLocal() as session:
        return await CuisineService.list_cuisines(session, limit, offset)


@router.get(
    "/cuisines/{cuisine_id}",
    response_model=CuisineResponse,
    summary="Get Cuisine by ID"
)
async def get_cuisine(cuisine_id: int):
    async with AsyncSessionLocal() as session:
        cuisine = await CuisineService.get_cuisine(session, cuisine_id)
        if not cuisine:
            raise HTTPException(status_code=404, detail="Cuisine not found")
        return cuisine


@router.post(
    "/cuisines",
    response_model=CuisineResponse,
    summary="Create New Cuisine"
)
async def create_cuisine(data: CuisineCreate):
    async with AsyncSessionLocal() as session:
        try:
            return await CuisineService.create_cuisine(session, data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/cuisines/{cuisine_id}",
    response_model=CuisineResponse,
    summary="Update Cuisine"
)
async def update_cuisine(cuisine_id: int, data: CuisineUpdate):
    async with AsyncSessionLocal() as session:
        try:
            return await CuisineService.update_cuisine(session, cuisine_id, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/cuisines/{cuisine_id}",
    summary="Delete Cuisine"
)
async def delete_cuisine(cuisine_id: int, permanent: bool = Query(False)):
    async with AsyncSessionLocal() as session:
        try:
            return await CuisineService.delete_cuisine(session, cuisine_id, permanent)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============================================================================
# REFERENCE TABLES (FOOD ROLES & GOALS)
# ============================================================================

def create_generic_routes(router, prefix, tags, service_cls, create_schema, update_schema, response_schema, list_response_schema):
    @router.get(f"/{prefix}", response_model=list_response_schema, tags=tags)
    async def list_items(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
        async with AsyncSessionLocal() as session:
            return await service_cls.list(session, limit, offset)

    @router.get(f"/{prefix}/{{item_id}}", response_model=response_schema, tags=tags)
    async def get_item(item_id: int):
        async with AsyncSessionLocal() as session:
            item = await service_cls.get(session, item_id)
            if not item: raise HTTPException(status_code=404, detail="Item not found")
            return item

    @router.post(f"/{prefix}", response_model=response_schema, tags=tags)
    async def create_item(data: create_schema):
        async with AsyncSessionLocal() as session:
            try: return await service_cls.create(session, data)
            except Exception as e: raise HTTPException(status_code=400, detail=str(e))

    @router.put(f"/{prefix}/{{item_id}}", response_model=response_schema, tags=tags)
    async def update_item(item_id: int, data: update_schema):
        async with AsyncSessionLocal() as session:
            try: return await service_cls.update(session, item_id, data)
            except AppException as e: raise HTTPException(status_code=e.status_code, detail=e.detail)

    @router.delete(f"/{prefix}/{{item_id}}", tags=tags)
    async def delete_item(item_id: int, permanent: bool = Query(False)):
        async with AsyncSessionLocal() as session:
            try: return await service_cls.delete(session, item_id, permanent)
            except AppException as e: raise HTTPException(status_code=e.status_code, detail=e.detail)

create_generic_routes(router, "food-roles", ["Admin Data Entry - Reference"], FoodRoleService, FoodRoleCreate, FoodRoleUpdate, FoodRoleResponse, FoodRoleListResponse)
create_generic_routes(router, "primary-goals", ["Admin Data Entry - Reference"], PrimaryGoalService, PrimaryGoalCreate, PrimaryGoalUpdate, PrimaryGoalResponse, PrimaryGoalListResponse)
create_generic_routes(router, "secondary-goals", ["Admin Data Entry - Reference"], SecondaryGoalService, SecondaryGoalCreate, SecondaryGoalUpdate, SecondaryGoalResponse, SecondaryGoalListResponse)

# ============================================================================
# MEAL SESSIONS
# ============================================================================

@router.get(
    "/meal-sessions",
    response_model=MealSessionListResponse,
    summary="List All Meal Sessions",
    description="Retrieve all meal sessions (breakfast, lunch, dinner, etc.)"
)
async def list_meal_sessions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    async with AsyncSessionLocal() as session:
        return await MealSessionService.list_meal_sessions(session, limit, offset)


@router.get(
    "/meal-sessions/{session_id}",
    response_model=MealSessionResponse,
    summary="Get Meal Session by ID"
)
async def get_meal_session(session_id: int):
    async with AsyncSessionLocal() as session:
        meal_session = await MealSessionService.get_meal_session(session, session_id)
        if not meal_session:
            raise HTTPException(status_code=404, detail="Meal session not found")
        return meal_session


@router.post(
    "/meal-sessions",
    response_model=MealSessionResponse,
    summary="Create New Meal Session"
)
async def create_meal_session(data: MealSessionCreate):
    async with AsyncSessionLocal() as session:
        try:
            return await MealSessionService.create_meal_session(session, data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/meal-sessions/{session_id}",
    response_model=MealSessionResponse,
    summary="Update Meal Session"
)
async def update_meal_session(session_id: int, data: MealSessionUpdate):
    async with AsyncSessionLocal() as session:
        try:
            return await MealSessionService.update_meal_session(session, session_id, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/meal-sessions/{session_id}",
    summary="Delete Meal Session"
)
async def delete_meal_session(session_id: int, permanent: bool = Query(False)):
    async with AsyncSessionLocal() as session:
        try:
            return await MealSessionService.delete_meal_session(session, session_id, permanent)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============================================================================
# INGREDIENTS
# ============================================================================

@router.get(
    "/ingredients",
    response_model=MasterIngredientListResponse,
    summary="List All Master Ingredients",
    description="Retrieve all ingredients with nutritional information."
)
async def list_ingredients(
    limit: int = Query(100, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True)
):
    async with AsyncSessionLocal() as session:
        return await MasterIngredientService.list_ingredients(session, limit, offset, active_only)


@router.get(
    "/ingredients/{ingredient_id}",
    response_model=MasterIngredientResponse,
    summary="Get Ingredient by ID"
)
async def get_ingredient(ingredient_id: int):
    async with AsyncSessionLocal() as session:
        ingredient = await MasterIngredientService.get_ingredient(session, ingredient_id)
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        return ingredient


@router.post(
    "/ingredients",
    response_model=MasterIngredientResponse,
    summary="Create New Ingredient",
    description="Add a new master ingredient with nutritional macros and micronutrients."
)
async def create_ingredient(data: MasterIngredientCreate):
    async with AsyncSessionLocal() as session:
        try:
            return await MasterIngredientService.create_ingredient(session, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/ingredients/{ingredient_id}",
    response_model=MasterIngredientResponse,
    summary="Update Ingredient"
)
async def update_ingredient(ingredient_id: int, data: MasterIngredientUpdate):
    async with AsyncSessionLocal() as session:
        try:
            return await MasterIngredientService.update_ingredient(session, ingredient_id, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/ingredients/{ingredient_id}",
    summary="Delete Ingredient"
)
async def delete_ingredient(ingredient_id: int, permanent: bool = Query(False)):
    async with AsyncSessionLocal() as session:
        try:
            return await MasterIngredientService.delete_ingredient(session, ingredient_id, permanent)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============================================================================
# FOODS
# ============================================================================

@router.get(
    "/foods",
    response_model=FoodListResponse,
    summary="List All Foods",
    description="Retrieve all foods (composite dishes) with optional cuisine filtering."
)
async def list_foods(
    cuisine_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None)
):
    async with AsyncSessionLocal() as session:
        return await FoodService.list_foods(session, cuisine_id, limit, offset, active_only, search)


@router.get(
    "/foods/{food_id}",
    response_model=FoodResponse,
    summary="Get Food by ID"
)
async def get_food(food_id: int):
    async with AsyncSessionLocal() as session:
        food = await FoodService.get_food(session, food_id)
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        return food


@router.post(
    "/foods",
    response_model=FoodResponse,
    summary="Create New Food",
    description="Create a new food (composite dish) with ingredient composition."
)
async def create_food(data: FoodCreate):
    async with AsyncSessionLocal() as session:
        try:
            return await FoodService.create_food(session, data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/foods/{food_id}",
    response_model=FoodResponse,
    summary="Update Food",
    description="Update food details and/or ingredient composition."
)
async def update_food(food_id: int, data: FoodUpdate):
    async with AsyncSessionLocal() as session:
        try:
            return await FoodService.update_food(session, food_id, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/foods/{food_id}",
    summary="Delete Food"
)
async def delete_food(food_id: int, permanent: bool = Query(False)):
    async with AsyncSessionLocal() as session:
        try:
            return await FoodService.delete_food(session, food_id, permanent)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


# ============================================================================
# MEALS
# ============================================================================

@router.get(
    "/meals",
    response_model=MealListResponse,
    summary="List All Meals",
    description="Retrieve all meals (recipes) with optional cuisine filtering."
)
async def list_meals(
    cuisine_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None)
):
    async with AsyncSessionLocal() as session:
        return await MealService.list_meals(session, cuisine_id, limit, offset, active_only, search)


@router.get(
    "/meals/{meal_id}",
    response_model=MealResponse,
    summary="Get Meal by ID"
)
async def get_meal(meal_id: int):
    async with AsyncSessionLocal() as session:
        meal = await MealService.get_meal(session, meal_id)
        if not meal:
            raise HTTPException(status_code=404, detail="Meal not found")
        return meal


@router.post(
    "/meals",
    response_model=MealResponse,
    summary="Create New Meal",
    description="Create a new meal (recipe) composed of foods."
)
async def create_meal(data: MealCreate):
    async with AsyncSessionLocal() as session:
        try:
            return await MealService.create_meal(session, data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/meals/{meal_id}",
    response_model=MealResponse,
    summary="Update Meal",
    description="Update meal details and/or food composition."
)
async def update_meal(meal_id: int, data: MealUpdate):
    async with AsyncSessionLocal() as session:
        try:
            return await MealService.update_meal(session, meal_id, data)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)


@router.delete(
    "/meals/{meal_id}",
    summary="Delete Meal"
)
async def delete_meal(meal_id: int, permanent: bool = Query(False)):
    async with AsyncSessionLocal() as session:
        try:
            return await MealService.delete_meal(session, meal_id, permanent)
        except AppException as e:
            raise HTTPException(status_code=e.status_code, detail=e.detail)
