"""
Admin CRUD service layer for database operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from database.models.catalog import (
    Cuisine, MealSession, MasterIngredient, Food, FoodIngredient, Meal, MealFood
)
from admin.schemas import (
    CuisineCreate, CuisineUpdate, CuisineResponse,
    MealSessionCreate, MealSessionUpdate, MealSessionResponse,
    MasterIngredientCreate, MasterIngredientUpdate, MasterIngredientResponse,
    FoodCreate, FoodUpdate, FoodResponse,
    MealCreate, MealUpdate, MealResponse,
)
from exceptions.base import AppException


class CuisineService:
    @staticmethod
    async def list_cuisines(session: AsyncSession, limit: int = 100, offset: int = 0):
        query = select(Cuisine).order_by(Cuisine.sort_order, Cuisine.id)
        result = await session.execute(query.limit(limit).offset(offset))
        cuisines = result.scalars().all()
        
        count_result = await session.execute(select(Cuisine))
        total = len(count_result.scalars().all())
        
        return {"total": total, "items": cuisines}

    @staticmethod
    async def get_cuisine(session: AsyncSession, cuisine_id: int) -> Optional[Cuisine]:
        result = await session.execute(
            select(Cuisine).where(Cuisine.id == cuisine_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_cuisine(session: AsyncSession, data: CuisineCreate) -> Cuisine:
        cuisine = Cuisine(**data.model_dump())
        session.add(cuisine)
        await session.commit()
        await session.refresh(cuisine)
        return cuisine

    @staticmethod
    async def update_cuisine(session: AsyncSession, cuisine_id: int, data: CuisineUpdate) -> Cuisine:
        cuisine = await CuisineService.get_cuisine(session, cuisine_id)
        if not cuisine:
            raise AppException(f"Cuisine {cuisine_id} not found", status_code=404)
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cuisine, key, value)
        
        await session.commit()
        await session.refresh(cuisine)
        return cuisine

    @staticmethod
    async def delete_cuisine(session: AsyncSession, cuisine_id: int, permanent: bool = False):
        cuisine = await CuisineService.get_cuisine(session, cuisine_id)
        if not cuisine:
            raise AppException(f"Cuisine {cuisine_id} not found", status_code=404)
        
        if permanent:
            await session.delete(cuisine)
        else:
            cuisine.is_active = False
        await session.commit()
        return {"message": "Cuisine deleted successfully" if not permanent else "Cuisine permanently deleted successfully"}


class MealSessionService:
    @staticmethod
    async def list_meal_sessions(session: AsyncSession, limit: int = 100, offset: int = 0):
        query = select(MealSession).order_by(MealSession.sort_order, MealSession.id)
        result = await session.execute(query.limit(limit).offset(offset))
        sessions = result.scalars().all()
        
        count_result = await session.execute(select(MealSession))
        total = len(count_result.scalars().all())
        
        return {"total": total, "items": sessions}

    @staticmethod
    async def get_meal_session(session: AsyncSession, session_id: int) -> Optional[MealSession]:
        result = await session.execute(
            select(MealSession).where(MealSession.id == session_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_meal_session(session: AsyncSession, data: MealSessionCreate) -> MealSession:
        meal_session = MealSession(**data.model_dump())
        session.add(meal_session)
        await session.commit()
        await session.refresh(meal_session)
        return meal_session

    @staticmethod
    async def update_meal_session(session: AsyncSession, session_id: int, data: MealSessionUpdate) -> MealSession:
        meal_session = await MealSessionService.get_meal_session(session, session_id)
        if not meal_session:
            raise AppException(f"Meal session {session_id} not found", status_code=404)
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(meal_session, key, value)
        
        await session.commit()
        await session.refresh(meal_session)
        return meal_session

    @staticmethod
    async def delete_meal_session(session: AsyncSession, session_id: int, permanent: bool = False):
        meal_session = await MealSessionService.get_meal_session(session, session_id)
        if not meal_session:
            raise AppException(f"Meal session {session_id} not found", status_code=404)
        
        if permanent:
            await session.delete(meal_session)
        else:
            meal_session.is_active = False
        await session.commit()
        return {"message": "Meal session deleted successfully" if not permanent else "Meal session permanently deleted successfully"}


class MasterIngredientService:
    @staticmethod
    async def list_ingredients(session: AsyncSession, limit: int = 100, offset: int = 0, active_only: bool = True):
        query = select(MasterIngredient).order_by(desc(MasterIngredient.id))
        if active_only:
            query = query.where(MasterIngredient.is_active == True)
        
        result = await session.execute(query.limit(limit).offset(offset))
        ingredients = result.scalars().all()
        
        count_query = select(MasterIngredient)
        if active_only:
            count_query = count_query.where(MasterIngredient.is_active == True)
        count_result = await session.execute(count_query)
        total = len(count_result.scalars().all())
        
        return {"total": total, "items": ingredients}

    @staticmethod
    async def get_ingredient(session: AsyncSession, ingredient_id: int) -> Optional[MasterIngredient]:
        result = await session.execute(
            select(MasterIngredient).where(MasterIngredient.id == ingredient_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_ingredient(session: AsyncSession, data: MasterIngredientCreate) -> MasterIngredient:
        # Check duplicate name_en case-insensitively
        name_stripped = data.name_en.strip()
        query = select(MasterIngredient).where(
            MasterIngredient.name_en.ilike(name_stripped)
        )
        existing = await session.execute(query)
        if existing.scalar_one_or_none():
            raise AppException(f"An ingredient named '{data.name_en}' already exists.", status_code=400)

        ingredient = MasterIngredient(**data.model_dump())
        session.add(ingredient)
        await session.commit()
        await session.refresh(ingredient)
        return ingredient

    @staticmethod
    async def update_ingredient(session: AsyncSession, ingredient_id: int, data: MasterIngredientUpdate) -> MasterIngredient:
        ingredient = await MasterIngredientService.get_ingredient(session, ingredient_id)
        if not ingredient:
            raise AppException(f"Ingredient {ingredient_id} not found", status_code=404)
        
        if data.name_en is not None:
            name_stripped = data.name_en.strip()
            query = select(MasterIngredient).where(
                MasterIngredient.name_en.ilike(name_stripped),
                MasterIngredient.id != ingredient_id
            )
            existing = await session.execute(query)
            if existing.scalar_one_or_none():
                raise AppException(f"An ingredient named '{data.name_en}' already exists.", status_code=400)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ingredient, key, value)
        
        await session.commit()
        await session.refresh(ingredient)
        return ingredient

    @staticmethod
    async def delete_ingredient(session: AsyncSession, ingredient_id: int, permanent: bool = False):
        ingredient = await MasterIngredientService.get_ingredient(session, ingredient_id)
        if not ingredient:
            raise AppException(f"Ingredient {ingredient_id} not found", status_code=404)
        
        if permanent:
            await session.delete(ingredient)
        else:
            # Soft delete
            ingredient.is_active = False
            ingredient.deleted_at = datetime.utcnow()
        await session.commit()
        return {"message": "Ingredient deleted successfully" if not permanent else "Ingredient permanently deleted successfully"}


class FoodService:
    @staticmethod
    async def list_foods(session: AsyncSession, cuisine_id: Optional[int] = None, limit: int = 100, offset: int = 0, active_only: bool = True, search: Optional[str] = None):
        query = select(Food).options(selectinload(Food.food_ingredients)).order_by(Food.id)
        
        if active_only:
            query = query.where(Food.is_active == True)
        if cuisine_id:
            query = query.where(Food.cuisine_id == cuisine_id)
            
        count_query = select(Food)
        if active_only:
            count_query = count_query.where(Food.is_active == True)
        if cuisine_id:
            count_query = count_query.where(Food.cuisine_id == cuisine_id)

        if search:
            search_stripped = search.strip()
            id_filter = None
            if search_stripped.isdigit():
                id_filter = (Food.id == int(search_stripped))
            
            search_cond = (
                Food.name_en.ilike(f"%{search_stripped}%") |
                Food.name_ar.ilike(f"%{search_stripped}%") |
                Food.client_food_id.ilike(f"%{search_stripped}%") |
                Food.food_role.ilike(f"%{search_stripped}%")
            )
            if id_filter is not None:
                search_cond = id_filter | search_cond
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)
        
        result = await session.execute(query.limit(limit).offset(offset))
        foods = result.scalars().all()
        
        count_result = await session.execute(count_query)
        total = len(count_result.scalars().all())
        
        return {"total": total, "items": foods}

    @staticmethod
    async def get_food(session: AsyncSession, food_id: int) -> Optional[Food]:
        result = await session.execute(
            select(Food).options(selectinload(Food.food_ingredients)).where(Food.id == food_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_food(session: AsyncSession, data: FoodCreate) -> Food:
        food_dict = data.model_dump(exclude={"food_ingredients"})
        food = Food(**food_dict)
        session.add(food)
        await session.flush()
        
        # Add food ingredients
        for fi in data.food_ingredients:
            food_ingredient = FoodIngredient(
                food_id=food.id,
                ingredient_id=fi.ingredient_id,
                quantity=fi.quantity,
                sort_order=fi.sort_order
            )
            session.add(food_ingredient)
        
        await session.commit()
        return await FoodService.get_food(session, food.id)

    @staticmethod
    async def update_food(session: AsyncSession, food_id: int, data: FoodUpdate) -> Food:
        food = await FoodService.get_food(session, food_id)
        if not food:
            raise AppException(f"Food {food_id} not found", status_code=404)
        
        update_data = data.model_dump(exclude_unset=True, exclude={"food_ingredients"})
        for key, value in update_data.items():
            setattr(food, key, value)
        
        # Update food ingredients if provided
        if data.food_ingredients is not None:
            await session.execute(
                delete(FoodIngredient).where(FoodIngredient.food_id == food_id)
            )
            for fi in data.food_ingredients:
                food_ingredient = FoodIngredient(
                    food_id=food_id,
                    ingredient_id=fi.ingredient_id,
                    quantity=fi.quantity,
                    sort_order=fi.sort_order
                )
                session.add(food_ingredient)
        
        await session.commit()
        return await FoodService.get_food(session, food.id)

    @staticmethod
    async def delete_food(session: AsyncSession, food_id: int, permanent: bool = False):
        food = await FoodService.get_food(session, food_id)
        if not food:
            raise AppException(f"Food {food_id} not found", status_code=404)
        
        if permanent:
            await session.delete(food)
        else:
            # Soft delete
            food.is_active = False
            food.deleted_at = datetime.utcnow()
        await session.commit()
        return {"message": "Food deleted successfully" if not permanent else "Food permanently deleted successfully"}


class MealService:
    @staticmethod
    async def list_meals(session: AsyncSession, cuisine_id: Optional[int] = None, limit: int = 100, offset: int = 0, active_only: bool = True, search: Optional[str] = None):
        query = select(Meal).options(
            selectinload(Meal.meal_foods)
            .selectinload(MealFood.food)
            .selectinload(Food.food_ingredients)
        ).order_by(Meal.id)
        
        if active_only:
            query = query.where(Meal.is_active == True)
        if cuisine_id:
            query = query.where(Meal.cuisine_id == cuisine_id)
            
        count_query = select(Meal)
        if active_only:
            count_query = count_query.where(Meal.is_active == True)
        if cuisine_id:
            count_query = count_query.where(Meal.cuisine_id == cuisine_id)

        if search:
            search_stripped = search.strip()
            id_filter = None
            if search_stripped.isdigit():
                id_filter = (Meal.id == int(search_stripped))
            
            search_cond = (
                Meal.name_en.ilike(f"%{search_stripped}%") |
                Meal.name_ar.ilike(f"%{search_stripped}%") |
                Meal.client_meal_id.ilike(f"%{search_stripped}%")
            )
            if id_filter is not None:
                search_cond = id_filter | search_cond
            query = query.where(search_cond)
            count_query = count_query.where(search_cond)
        
        result = await session.execute(query.limit(limit).offset(offset))
        meals = result.scalars().all()
        
        count_result = await session.execute(count_query)
        total = len(count_result.scalars().all())
        
        return {"total": total, "items": meals}

    @staticmethod
    async def get_meal(session: AsyncSession, meal_id: int) -> Optional[Meal]:
        result = await session.execute(
            select(Meal).options(
                selectinload(Meal.meal_foods)
                .selectinload(MealFood.food)
                .selectinload(Food.food_ingredients)
            ).where(Meal.id == meal_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_meal(session: AsyncSession, data: MealCreate) -> Meal:
        meal_dict = data.model_dump(exclude={"meal_foods"})
        meal = Meal(**meal_dict)
        session.add(meal)
        await session.flush()
        
        # Add meal foods
        for mf in data.meal_foods:
            meal_food = MealFood(
                meal_id=meal.id,
                food_id=mf.food_id,
                is_replaceable=mf.is_replaceable,
                sort_order=mf.sort_order
            )
            session.add(meal_food)
        
        await session.commit()
        return await MealService.get_meal(session, meal.id)

    @staticmethod
    async def update_meal(session: AsyncSession, meal_id: int, data: MealUpdate) -> Meal:
        meal = await MealService.get_meal(session, meal_id)
        if not meal:
            raise AppException(f"Meal {meal_id} not found", status_code=404)
        
        update_data = data.model_dump(exclude_unset=True, exclude={"meal_foods"})
        for key, value in update_data.items():
            setattr(meal, key, value)
        
        # Update meal foods if provided
        if data.meal_foods is not None:
            await session.execute(
                delete(MealFood).where(MealFood.meal_id == meal_id)
            )
            for mf in data.meal_foods:
                meal_food = MealFood(
                    meal_id=meal_id,
                    food_id=mf.food_id,
                    is_replaceable=mf.is_replaceable,
                    sort_order=mf.sort_order
                )
                session.add(meal_food)
        
        await session.commit()
        return await MealService.get_meal(session, meal.id)

    @staticmethod
    async def delete_meal(session: AsyncSession, meal_id: int, permanent: bool = False):
        meal = await MealService.get_meal(session, meal_id)
        if not meal:
            raise AppException(f"Meal {meal_id} not found", status_code=404)
        
        if permanent:
            await session.delete(meal)
        else:
            # Soft delete
            meal.is_active = False
            meal.deleted_at = datetime.utcnow()
        await session.commit()
        return {"message": "Meal deleted successfully" if not permanent else "Meal permanently deleted successfully"}
