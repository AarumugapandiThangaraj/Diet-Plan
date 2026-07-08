import asyncio
import sys
from pathlib import Path
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parent))
from database.session import engine

async def migrate():
    async with engine.begin() as conn:
        statements = [
            # Drop from diet_plan_meal_foods
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS calories_kcal;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS protein_g;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS carbs_g;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS fat_g;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS fiber_g;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS supports;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS supports_normalized;",
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meal_foods DROP COLUMN IF EXISTS sort_order;",
            
            # Drop from diet_plan_meals
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_meals DROP COLUMN IF EXISTS sort_order;",
            
            # Drop from diet_plan_days
            "ALTER TABLE \"Twellr_Nutri\".diet_plan_days DROP COLUMN IF EXISTS plan_date;"
        ]
        
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
                print(f"Executed: {stmt}")
            except Exception as e:
                print(f"Failed to execute {stmt}: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
