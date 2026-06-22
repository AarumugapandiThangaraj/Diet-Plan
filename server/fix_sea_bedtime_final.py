import asyncio
import json
from pathlib import Path
from sqlalchemy import select, text, delete
from database.session import AsyncSessionLocal
from database.models.catalog import Meal, MealFood

async def fix():
    async with AsyncSessionLocal() as session:
        # Get southeast_asian cuisine id
        c_res = await session.execute(text("SELECT id FROM \"Twellr_Nutri\".cuisines WHERE code = 'southeast_asian'"))
        cuisine_id = c_res.scalar()
        
        if not cuisine_id:
            print("Cuisine not found.")
            return

        # 1. Delete all bedtime meals for southeast_asian
        await session.execute(text(f"DELETE FROM \"Twellr_Nutri\".meals WHERE cuisine_id = {cuisine_id} AND meal_session_id = 7"))
        await session.commit()
        print("Deleted existing bedtime meals (including the evening duplicates).")

        # 2. Read meals.json
        data_path = Path('d:/IAgami/Bioart Dataset/Diet Plan Updated/Diet-Plan-Pull Only/Diet-Plan/migration_backup/original_json_datasets/Mealsdata/Southeast Asia/meals.json')
        data = json.loads(data_path.read_text(encoding='utf-8'))
        
        # 3. Find true Bed Time meals
        bedtime_meals = []
        for m in data:
            if "Bed Time" in m.get("Session", []):
                bedtime_meals.append(m)
                
        print(f"Found {len(bedtime_meals)} Bed Time meals in JSON.")
        
        # 4. Insert them into DB
        for idx, m in enumerate(bedtime_meals):
            # assign a truly unique ID
            new_client_id = f"MEAL_SEA_BT_ACTUAL_{idx+1:03d}"
            
            new_meal = Meal(
                cuisine_id=cuisine_id,
                client_meal_id=new_client_id,
                name_en=m.get("Name", "").strip(),
                description_en=m.get("Description", "").strip(),
                meal_session_id=7, # bedtime
                diet_types=m.get("Diet Type", []),
                goal=m.get("Goal", [])
            )
            session.add(new_meal)
            await session.flush()
            
            # Map foods
            for f in m.get("Foods", []):
                client_food_id = f.get("ID")
                # find food in DB
                f_res = await session.execute(text(f"SELECT id FROM \"Twellr_Nutri\".foods WHERE client_food_id = '{client_food_id}' AND cuisine_id = {cuisine_id}"))
                db_food_id = f_res.scalar()
                
                if not db_food_id:
                    print(f"Warning: Food {client_food_id} not found in DB for meal {new_client_id}. Skipping.")
                    continue
                    
                mf = MealFood(
                    meal_id=new_meal.id,
                    food_id=db_food_id,
                    is_replaceable=f.get("Replaceable", True)
                )
                session.add(mf)
                
        await session.commit()
        print("Successfully inserted the true Bed Time meals into the DB!")

asyncio.run(fix())
