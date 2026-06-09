import sys
import asyncio
from pathlib import Path
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add backend directory to Python path
backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Create in-memory async SQLite engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Patch the database session module directly BEFORE any backend code is imported
import database.session
database.session.AsyncSessionLocal = TestAsyncSessionLocal
database.session.engine = test_engine

# Now safe to import backend app and models
from database.base import Base
from app import app
from database.models.substitute import Substitute
from database.models.cuisine import Cuisine
from database.models.ingredient import Ingredient
from database.models.food import Food, FoodIngredient
from database.models.meal import Meal, MealFood

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Seed reference data so FastAPI startup validation passes and tests have base data
        async with TestAsyncSessionLocal() as session:
            sub = Substitute(
                id="SUB_DEFAULT",
                allergen_category="default_category",
                allergen_name="default",
                substitutes=[]
            )
            session.add(sub)
            
            cuisine = Cuisine(id=1, name="north_indian")
            session.add(cuisine)
            
            ingredient = Ingredient(
                id="ING_1",
                name="Tomato",
                default_unit="g",
                calories=18.0,
                protein=0.9,
                carbs=3.9,
                fat=0.2,
                fiber=1.2
            )
            session.add(ingredient)
            
            food = Food(
                id="FOOD_1",
                name="Tomato Soup",
                cuisine_id=1,
                quantity=100.0,
                unit="g",
                calories=30.0,
                protein=1.0,
                carbs=6.0,
                fat=0.5,
                fiber=1.0
            )
            session.add(food)
            await session.flush()
            
            fi = FoodIngredient(
                food_id="FOOD_1",
                ingredient_id="ING_1",
                quantity=100.0,
                unit="g",
                swapable=True
            )
            session.add(fi)
            
            meal = Meal(
                id="MEAL_1",
                name="Tomato Soup Dinner",
                cuisine_id=1,
                sessions=["dinner"],
                calories=30.0,
                protein=1.0,
                carbs=6.0,
                fat=0.5,
                fiber=1.0
            )
            session.add(meal)
            await session.flush()
            
            mf = MealFood(
                meal_id="MEAL_1",
                food_id="FOOD_1",
                quantity=100.0,
                unit="g",
                replaceable=True
            )
            session.add(mf)
            await session.commit()
            
    async def drop_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
    loop = asyncio.new_event_loop()
    loop.run_until_complete(create_tables())
    yield
    loop.run_until_complete(drop_tables())
    loop.close()

@pytest.fixture(autouse=True)
def patch_db_session():
    with patch("database.session.AsyncSessionLocal", TestAsyncSessionLocal), \
         patch("database.session.engine", test_engine), \
         patch("repositories.chat_repository.AsyncSessionLocal", TestAsyncSessionLocal), \
         patch("repositories.substitute_repository.AsyncSessionLocal", TestAsyncSessionLocal), \
         patch("repositories.meal_repository.AsyncSessionLocal", TestAsyncSessionLocal):
        yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_profile_male():
    return {
        "age": 30,
        "gender": "male",
        "heightCm": 175,
        "weightKg": 75,
        "activityLevel": "moderate",
        "cuisineType": "north_indian",
        "goal": "hair_repair",
        "mealTimes": ["breakfast", "lunch", "dinner"]
    }

@pytest.fixture
def mock_profile_female():
    return {
        "age": 25,
        "gender": "female",
        "heightCm": 160,
        "weightKg": 50,
        "activityLevel": "sedentary",
        "cuisineType": "south_indian",
        "goal": "skin_repair",
        "mealTimes": ["breakfast", "lunch", "evening", "dinner"]
    }
