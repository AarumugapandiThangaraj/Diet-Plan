"""
Admin CRUD service layer for database operations
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime


from database.models.catalog import (
    Cuisine, MealSession, Food, Meal, MealFood,
    FoodRole, PrimaryGoal, SecondaryGoal, MealPrimaryGoal, MealSecondaryGoal
)
from admin.schemas import (
    CuisineCreate, CuisineUpdate, CuisineResponse,
    MealSessionCreate, MealSessionUpdate, MealSessionResponse,
    FoodCreate, FoodUpdate, FoodResponse,
    MealCreate, MealUpdate, MealResponse,
    FoodRoleCreate, FoodRoleUpdate, PrimaryGoalCreate, PrimaryGoalUpdate, SecondaryGoalCreate, SecondaryGoalUpdate
)
from exceptions.base import AppException

class GenericLookupService:
    @staticmethod
    async def list_items(session: AsyncSession, model_cls, limit: int = 100, offset: int = 0):
        query = select(model_cls).order_by(model_cls.id)
        result = await session.execute(query.limit(limit).offset(offset))
        items = result.scalars().all()
        count_result = await session.execute(select(model_cls))
        total = len(count_result.scalars().all())
        return {"total": total, "items": items}

    @staticmethod
    async def get_item(session: AsyncSession, model_cls, item_id: int):
        result = await session.execute(select(model_cls).where(model_cls.id == item_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_item(session: AsyncSession, model_cls, data):
        item = model_cls(**data.model_dump())
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def update_item(session: AsyncSession, model_cls, item_id: int, data):
        item = await GenericLookupService.get_item(session, model_cls, item_id)
        if not item:
            raise AppException(f"Item {item_id} not found", status_code=404)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(item, key, value)
        await session.commit()
        await session.refresh(item)
        return item

    @staticmethod
    async def delete_item(session: AsyncSession, model_cls, item_id: int, permanent: bool = False):
        item = await GenericLookupService.get_item(session, model_cls, item_id)
        if not item:
            raise AppException(f"Item {item_id} not found", status_code=404)
        if permanent:
            await session.delete(item)
        else:
            item.is_active = False
        await session.commit()
        return {"message": "Item deleted successfully"}

class FoodRoleService:
    @staticmethod
    async def list(session: AsyncSession, limit: int = 100, offset: int = 0): return await GenericLookupService.list_items(session, FoodRole, limit, offset)
    @staticmethod
    async def get(session: AsyncSession, item_id: int): return await GenericLookupService.get_item(session, FoodRole, item_id)
    @staticmethod
    async def create(session: AsyncSession, data: FoodRoleCreate): return await GenericLookupService.create_item(session, FoodRole, data)
    @staticmethod
    async def update(session: AsyncSession, item_id: int, data: FoodRoleUpdate): return await GenericLookupService.update_item(session, FoodRole, item_id, data)
    @staticmethod
    async def delete(session: AsyncSession, item_id: int, permanent: bool = False): return await GenericLookupService.delete_item(session, FoodRole, item_id, permanent)

class PrimaryGoalService:
    @staticmethod
    async def list(session: AsyncSession, limit: int = 100, offset: int = 0): return await GenericLookupService.list_items(session, PrimaryGoal, limit, offset)
    @staticmethod
    async def get(session: AsyncSession, item_id: int): return await GenericLookupService.get_item(session, PrimaryGoal, item_id)
    @staticmethod
    async def create(session: AsyncSession, data: PrimaryGoalCreate): return await GenericLookupService.create_item(session, PrimaryGoal, data)
    @staticmethod
    async def update(session: AsyncSession, item_id: int, data: PrimaryGoalUpdate): return await GenericLookupService.update_item(session, PrimaryGoal, item_id, data)
    @staticmethod
    async def delete(session: AsyncSession, item_id: int, permanent: bool = False): return await GenericLookupService.delete_item(session, PrimaryGoal, item_id, permanent)

class SecondaryGoalService:
    @staticmethod
    async def list(session: AsyncSession, limit: int = 100, offset: int = 0): return await GenericLookupService.list_items(session, SecondaryGoal, limit, offset)
    @staticmethod
    async def get(session: AsyncSession, item_id: int): return await GenericLookupService.get_item(session, SecondaryGoal, item_id)
    @staticmethod
    async def create(session: AsyncSession, data: SecondaryGoalCreate): return await GenericLookupService.create_item(session, SecondaryGoal, data)
    @staticmethod
    async def update(session: AsyncSession, item_id: int, data: SecondaryGoalUpdate): return await GenericLookupService.update_item(session, SecondaryGoal, item_id, data)
    @staticmethod
    async def delete(session: AsyncSession, item_id: int, permanent: bool = False): return await GenericLookupService.delete_item(session, SecondaryGoal, item_id, permanent)


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
    pass

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
            query = query.outerjoin(Food.role)
            count_query = count_query.outerjoin(Food.role)
            search_stripped = search.strip()
            id_filter = None
            if search_stripped.isdigit():
                id_filter = (Food.id == int(search_stripped))
            
            search_cond = (
                Food.name_en.ilike(f"%{search_stripped}%") |
                Food.name_ar.ilike(f"%{search_stripped}%") |
                Food.client_food_id.ilike(f"%{search_stripped}%") |
                FoodRole.name_en.ilike(f"%{search_stripped}%")
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
    async def _calculate_food_nutrition(session: AsyncSession, food: Food, food_ingredients: list):
        pass

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
        # Recalculate nutrition
        await FoodService._calculate_food_nutrition(session, food, data.food_ingredients)
        
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
        # Recalculate nutrition if ingredients provided
        if data.food_ingredients is not None:
            await FoodService._calculate_food_nutrition(session, food, data.food_ingredients)
        
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
            .selectinload(Food.food_ingredients),
            selectinload(Meal.primary_goals),
            selectinload(Meal.secondary_goals)
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
                .selectinload(Food.food_ingredients),
                selectinload(Meal.primary_goals),
                selectinload(Meal.secondary_goals)
            ).where(Meal.id == meal_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _calculate_meal_nutrition(session: AsyncSession, meal: Meal, meal_foods: list):
        pass

    @staticmethod
    async def create_meal(session: AsyncSession, data: MealCreate) -> Meal:
        meal_dict = data.model_dump(exclude={"meal_foods", "primary_goal_ids", "secondary_goal_ids"})
        meal = Meal(**meal_dict)
        session.add(meal)
        await session.flush()
        
        # Add meal foods
        for mf in data.meal_foods:
            meal_food = MealFood(
                meal_id=meal.id,
                food_id=mf.food_id,
                quantity=mf.quantity,
                is_replaceable=mf.is_replaceable,
                sort_order=mf.sort_order
            )
            session.add(meal_food)
            
        # Add primary goals
        for pid in data.primary_goal_ids:
            session.add(MealPrimaryGoal(meal_id=meal.id, primary_goal_id=pid))
            
        # Add secondary goals
        for sid in data.secondary_goal_ids:
            session.add(MealSecondaryGoal(meal_id=meal.id, secondary_goal_id=sid))
        # Recalculate nutrition
        await MealService._calculate_meal_nutrition(session, meal, data.meal_foods)
        
        await session.commit()
        return await MealService.get_meal(session, meal.id)

    @staticmethod
    async def update_meal(session: AsyncSession, meal_id: int, data: MealUpdate) -> Meal:
        meal = await MealService.get_meal(session, meal_id)
        if not meal:
            raise AppException(f"Meal {meal_id} not found", status_code=404)
        
        update_data = data.model_dump(exclude_unset=True, exclude={"meal_foods", "primary_goal_ids", "secondary_goal_ids"})
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
                    quantity=mf.quantity,
                    is_replaceable=mf.is_replaceable,
                    sort_order=mf.sort_order
                )
                session.add(meal_food)
                
        # Update primary goals if provided
        if data.primary_goal_ids is not None:
            await session.execute(
                delete(MealPrimaryGoal).where(MealPrimaryGoal.meal_id == meal_id)
            )
            for pid in data.primary_goal_ids:
                session.add(MealPrimaryGoal(meal_id=meal.id, primary_goal_id=pid))
                
        # Update secondary goals if provided
        if data.secondary_goal_ids is not None:
            await session.execute(
                delete(MealSecondaryGoal).where(MealSecondaryGoal.meal_id == meal_id)
            )
            for sid in data.secondary_goal_ids:
                session.add(MealSecondaryGoal(meal_id=meal.id, secondary_goal_id=sid))
        # Recalculate nutrition if foods provided
        if data.meal_foods is not None:
            await MealService._calculate_meal_nutrition(session, meal, data.meal_foods)
            
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
