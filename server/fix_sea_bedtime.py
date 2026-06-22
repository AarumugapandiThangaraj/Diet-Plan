import asyncio
from sqlalchemy import text, select
from database.session import AsyncSessionLocal
from database.models.catalog import Meal, MealFood
from utils.normalizers import _normalize_meal_time

async def fix():
    async with AsyncSessionLocal() as session:
        # Get southeast_asian cuisine id
        c_res = await session.execute(text("SELECT id FROM \"Twellr_Nutri\".cuisines WHERE code = 'southeast_asian'"))
        cuisine_id = c_res.scalar()
        
        if not cuisine_id:
            print("Cuisine not found.")
            return

        # Check if bedtime meals already exist
        bt_res = await session.execute(text(f"SELECT count(*) FROM \"Twellr_Nutri\".meals WHERE cuisine_id = {cuisine_id} AND meal_session_id = 7"))
        bt_count = bt_res.scalar()
        if bt_count >= 30:
            print(f"Already {bt_count} bedtime meals for southeast_asian. Doing nothing.")
            return

        # Get the 30 evening meals
        stmt = select(Meal).where(Meal.cuisine_id == cuisine_id, Meal.meal_session_id == 5)
        res = await session.execute(stmt)
        evening_meals = res.scalars().all()

        print(f"Found {len(evening_meals)} evening meals to clone to bedtime.")
        
        for idx, em in enumerate(evening_meals[:30]):
            new_client_id = em.client_meal_id.replace("_E_", "_BT_")
            if "_BT_" not in new_client_id:
                new_client_id = f"MEAL_SEA_BT_{idx+1:03d}"
                
            new_meal = Meal(
                cuisine_id=em.cuisine_id,
                client_meal_id=new_client_id,
                name_en=em.name_en,
                description_en=em.description_en,
                meal_session_id=7, # bedtime
                diet_types=em.diet_types,
                goal=em.goal
            )
            session.add(new_meal)
            await session.flush()
            
            # Clone MealFoods
            mf_stmt = select(MealFood).where(MealFood.meal_id == em.id)
            mf_res = await session.execute(mf_stmt)
            for old_mf in mf_res.scalars().all():
                new_mf = MealFood(
                    meal_id=new_meal.id,
                    food_id=old_mf.food_id,
                    is_replaceable=old_mf.is_replaceable
                )
                session.add(new_mf)
                
        await session.commit()
        print("Successfully cloned evening meals to bedtime.")

asyncio.run(fix())
