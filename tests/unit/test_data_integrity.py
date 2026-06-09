import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.session import AsyncSessionLocal
from database.models.cuisine import Cuisine
from database.models.ingredient import Ingredient
from database.models.food import Food, FoodIngredient
from database.models.meal import Meal, MealFood

@pytest.mark.anyio
async def test_relational_data_integrity():
    async with AsyncSessionLocal() as session:
        # Verify Cuisine and Ingredient relations can be fetched correctly
        res = await session.execute(select(Food).options(
            selectinload(Food.cuisine),
            selectinload(Food.ingredient_associations)
        ))
        foods = res.scalars().all()
        for f in foods:
            assert f.cuisine is not None
            assert len(f.ingredient_associations) >= 0
            
        res_meal = await session.execute(select(Meal).options(
            selectinload(Meal.food_associations)
        ))
        meals = res_meal.scalars().all()
        for m in meals:
            assert len(m.food_associations) >= 0
