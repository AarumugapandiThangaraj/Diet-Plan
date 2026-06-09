"""
ETL Database Seed & Rebuild Pipeline

Initializes PostgreSQL tables, imports cuisines, ingredients (including conversion mappings),
foods, meals, and user preferences. Rebuilds and recompiles materialized food and meal
nutrition caches using standard unit density conversion rules.
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import settings
from database.base import Base
from database.session import engine, AsyncSessionLocal
from database.models.cuisine import Cuisine
from database.models.ingredient import Ingredient
from database.models.food import Food, FoodIngredient
from database.models.meal import Meal, MealFood
from database.models.preference import UserPreference
from database.models.substitute import Substitute

# Core constants
CUISINE_LIST = [
    "north_indian", "south_indian", "uae", "continental", "mediterranean",
    "african", "americas", "east_asian", "southeast_asian", "south_asian",
    "middle_eastern", "nordic", "oceania", "central", "russian", "fusion"
]

def clean_cuisine_name(filename: str, parent_name: str) -> str:
    combined = f"{parent_name}_{filename}".lower()
    for c in CUISINE_LIST:
        if c in combined or c.replace("_", "") in combined:
            return c
    if "north" in combined:
        return "north_indian"
    if "south" in combined:
        return "south_indian"
    return "north_indian"

async def init_db():
    print("Initializing Database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables initialized successfully.")

async def run_import():
    data_root = Path(__file__).resolve().parents[2] / "migration_backup" / "original_json_datasets"
    if not data_root.exists():
        print(f"Data root directory not found: {data_root}")
        return

    # Resolve image mapping from new assets mappings folder
    mapping_file = Path(settings.mapping_root) / "image_mapping.json"
    image_mapping = {}
    if mapping_file.exists():
        try:
            raw_map = json.loads(mapping_file.read_text(encoding="utf-8"))
            for cuisine_folder, files in raw_map.items():
                for filename, info in files.items():
                    fid = info.get("food_id")
                    if fid:
                        image_mapping[fid] = f"{cuisine_folder}/{filename}"
            print(f"Loaded {len(image_mapping)} food image mappings from new assets location.")
        except Exception as e:
            print(f"Error loading image mapping: {e}")

    await init_db()

    async with AsyncSessionLocal() as session:
        # 1. Cuisines
        print("Importing Cuisines...")
        cuisine_map: Dict[str, Cuisine] = {}
        for c_name in CUISINE_LIST:
            stmt = select(Cuisine).filter_by(name=c_name)
            res = await session.execute(stmt)
            cuisine_obj = res.scalar_one_or_none()
            if not cuisine_obj:
                cuisine_obj = Cuisine(name=c_name)
                session.add(cuisine_obj)
                await session.flush()
            cuisine_map[c_name] = cuisine_obj
        
        # 2. Ingredients
        print("Scanning and Importing Ingredients...")
        ingredient_files = list(data_root.rglob("*ingredient*.json"))
        loaded_ingredients: Dict[str, Dict[str, Any]] = {}
        
        for p in ingredient_files:
            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(content, dict) and "ingredients" in content:
                    content = content["ingredients"]
                elif isinstance(content, dict):
                    content = list(content.values())
                
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        ing_id = str(item.get("ID") or item.get("id") or "").strip()
                        name = str(item.get("Name") or item.get("name") or "").strip()
                        if ing_id and name:
                            loaded_ingredients[ing_id] = item
            except Exception as e:
                print(f"Error parsing ingredients file {p}: {e}")

        # Insert ingredients
        count = 0
        for ing_id, item in loaded_ingredients.items():
            stmt = select(Ingredient).filter_by(id=ing_id)
            res = await session.execute(stmt)
            if res.scalar_one_or_none():
                continue
            
            macros = item.get("Macros") or item.get("macros") or {}
            ing = Ingredient(
                id=ing_id,
                name=str(item.get("Name") or item.get("name") or "").strip(),
                default_unit=str(item.get("Default_Unit") or item.get("unit") or "g").strip(),
                calories=float(macros.get("Calories_kcal", macros.get("caloriesKcal", 0.0))),
                protein=float(macros.get("Protein_g", macros.get("proteinG", 0.0))),
                carbs=float(macros.get("Carbs_g", macros.get("carbsG", 0.0))),
                fat=float(macros.get("Fat_g", macros.get("fatG", 0.0))),
                fiber=float(macros.get("Fiber_g", macros.get("fiberG", 0.0))),
                micronutrients=item.get("Micronutrients") or item.get("micronutrients") or {},
                benefits=item.get("Benefits") or item.get("benefits") or {},
                category=str(item.get("Category") or "").strip(),
                main_name=str(item.get("main_name") or "").strip(),
                grup=str(item.get("grup") or item.get("group") or "").strip(),
                food_type=str(item.get("food_type") or "").strip(),
                food_state=str(item.get("food_state") or "").strip(),
                allergens=item.get("Allergens") or item.get("allergens") or [],
                caution=str(item.get("Caution") or "").strip(),
                notes=str(item.get("Notes") or "").strip()
            )
            session.add(ing)
            count += 1
            if count % 100 == 0:
                await session.flush()
        print(f"Successfully processed {count} new ingredients.")
        await session.commit()

        # 3. Foods & FoodIngredients
        print("Scanning and Importing Foods...")
        food_files = list(data_root.rglob("*food*.json"))
        loaded_foods: Dict[str, Dict[str, Any]] = {}

        for p in food_files:
            try:
                if "food_name_lists" in str(p) or "filtered_meals" in str(p):
                    continue
                cuisine_key = clean_cuisine_name(p.name, p.parent.name)
                content = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(content, dict) and "foods" in content:
                    content = content["foods"]
                elif isinstance(content, dict):
                    content = list(content.values())
                
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        f_id = str(item.get("ID") or item.get("id") or "").strip()
                        name = str(item.get("Name") or item.get("name") or "").strip()
                        if f_id and name:
                            item["_cuisine_key"] = cuisine_key
                            loaded_foods[f_id] = item
            except Exception as e:
                print(f"Error parsing food file {p}: {e}")

        # Insert Foods and relations
        food_count = 0
        rel_count = 0
        for f_id, item in loaded_foods.items():
            stmt = select(Food).filter_by(id=f_id)
            res = await session.execute(stmt)
            food_obj = res.scalar_one_or_none()
            
            cuisine_key = item.get("_cuisine_key", "north_indian")
            cuisine_obj = cuisine_map.get(cuisine_key)

            # Resolve image relative path for Food
            resolved_img = image_mapping.get(f_id)

            if not food_obj:
                macros = item.get("Nutritional_Info") or item.get("Nutritional_Info_per_Serving") or item.get("Nutritional_info") or {}
                food_obj = Food(
                    id=f_id,
                    name=str(item.get("Name") or item.get("name") or "").strip(),
                    cuisine_id=cuisine_obj.id if cuisine_obj else None,
                    description=str(item.get("Description") or "").strip(),
                    diet_types=item.get("Diet Type") or item.get("diet_type") or [],
                    quantity=float(item.get("Quantity") or 0.0),
                    min_quantity=float(item.get("Min_Quantity") or item.get("min_quantity") or 0.0) or None,
                    max_quantity=float(item.get("Max_Quantity") or item.get("max_quantity") or 0.0) or None,
                    unit=str(item.get("Unit") or "g").strip(),
                    supports=item.get("Supports") or [],
                    preparation=str(item.get("Preparation") or "").strip(),
                    notes=str(item.get("Notes") or "").strip(),
                    warning=bool(item.get("Warning") or False),
                    calories=0.0,
                    protein=0.0,
                    carbs=0.0,
                    fat=0.0,
                    fiber=0.0,
                    type=str(item.get("Type") or "").strip(),
                    image_url=resolved_img
                )
                session.add(food_obj)
                await session.flush()
                food_count += 1
            else:
                food_obj.image_url = resolved_img
            
            # Populate Food Ingredients mappings
            seen_ingredients_for_food: Set[str] = set()
            for ing_map in item.get("Ingredients") or item.get("ingredients") or []:
                if not isinstance(ing_map, dict):
                    continue
                ing_id = str(ing_map.get("Ingredient_ID") or ing_map.get("ingredient_id") or "").strip()
                if not ing_id:
                    continue
                if ing_id in seen_ingredients_for_food:
                    continue
                seen_ingredients_for_food.add(ing_id)
                
                # Check if association already exists
                stmt_ass = select(FoodIngredient).filter_by(food_id=f_id, ingredient_id=ing_id)
                res_ass = await session.execute(stmt_ass)
                if not res_ass.scalar_one_or_none():
                    # Double check ingredient exists
                    stmt_ing = select(Ingredient).filter_by(id=ing_id)
                    res_ing = await session.execute(stmt_ing)
                    if res_ing.scalar_one_or_none():
                        fi = FoodIngredient(
                            food_id=f_id,
                            ingredient_id=ing_id,
                            quantity=float(ing_map.get("Quantity") or ing_map.get("quantity") or 0.0),
                            unit=str(ing_map.get("Unit") or "g").strip(),
                            swapable=bool(ing_map.get("Swapable") or ing_map.get("swapable") or False)
                        )
                        session.add(fi)
                        rel_count += 1
        print(f"Processed {food_count} new foods and {rel_count} food-ingredient junctions.")
        await session.commit()


        # 4. Meals & MealFoods
        print("Scanning and Importing Meals...")
        meal_files = list(data_root.rglob("*meal*.json"))
        loaded_meals: Dict[str, Dict[str, Any]] = {}



        for p in meal_files:
            try:
                cuisine_key = clean_cuisine_name(p.name, p.parent.name)
                content = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(content, dict) and "meals" in content:
                    content = content["meals"]
                elif isinstance(content, dict):
                    content = list(content.values())
                
                if isinstance(content, list):
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        m_id = str(item.get("ID") or item.get("id") or "").strip()
                        name = str(item.get("Name") or item.get("name") or "").strip()
                        if m_id and name:
                            item["_cuisine_key"] = cuisine_key
                            loaded_meals[m_id] = item
            except Exception as e:
                print(f"Error parsing meal file {p}: {e}")

        meal_count = 0
        meal_food_count = 0
        for m_id, item in loaded_meals.items():
            stmt = select(Meal).filter_by(id=m_id)
            res = await session.execute(stmt)
            meal_obj = res.scalar_one_or_none()

            cuisine_key = item.get("_cuisine_key", "north_indian")
            cuisine_obj = cuisine_map.get(cuisine_key)

            # Resolve image if it exists in image_mapping
            resolved_img = ""
            for food_ref in item.get("Foods") or item.get("foods") or []:
                ref_id = str(food_ref.get("ID") or food_ref.get("id") or "").strip()
                if ref_id in image_mapping:
                    val = image_mapping[ref_id]
                    resolved_img = val.split("/")[-1] if "/" in val else val
                    break

            if not meal_obj:
                meal_obj = Meal(
                    id=m_id,
                    name=str(item.get("Name") or item.get("name") or "").strip(),
                    cuisine_id=cuisine_obj.id if cuisine_obj else None,
                    goal=item.get("Goal") or item.get("goal") or [],
                    diet_types=item.get("Diet Type") or item.get("diet_types") or item.get("diet_type") or [],
                    sessions=item.get("Session") or item.get("sessions") or item.get("session") or [],
                    scheduled_time=str(item.get("Time") or "").strip(),
                    description=str(item.get("Description") or "").strip(),
                    allergens=item.get("Allergens") or item.get("allergens") or [],
                    prep_time=str(item.get("PrepTime") or item.get("prep_time") or "").strip(),
                    tags=item.get("Tags") or item.get("tags") or [],
                    image_url=resolved_img
                )
                session.add(meal_obj)
                await session.flush()
                meal_count += 1
            
            # Map Meal Foods
            seen_foods_for_meal: Set[str] = set()
            for food_map in item.get("Foods") or item.get("foods") or []:
                if not isinstance(food_map, dict):
                    continue
                food_id = str(food_map.get("ID") or food_map.get("id") or "").strip()
                if not food_id:
                    continue
                if food_id in seen_foods_for_meal:
                    continue
                seen_foods_for_meal.add(food_id)

                stmt_mf = select(MealFood).filter_by(meal_id=m_id, food_id=food_id)
                res_mf = await session.execute(stmt_mf)
                if not res_mf.scalar_one_or_none():
                    # Verify food exists in DB
                    stmt_f = select(Food).filter_by(id=food_id)
                    res_f = await session.execute(stmt_f)
                    if res_f.scalar_one_or_none():
                        mf = MealFood(
                            meal_id=m_id,
                            food_id=food_id,
                            quantity=float(food_map.get("Quantity") or food_map.get("quantity") or 0.0),
                            unit=str(food_map.get("Unit") or "g").strip(),
                            replaceable=bool(food_map.get("Replaceable") or food_map.get("replaceable") or False)
                        )
                        session.add(mf)
                        meal_food_count += 1
        print(f"Processed {meal_count} new meals and {meal_food_count} meal-food junctions.")
        await session.commit()

        # 4.5 Recompile and Rebuild all Food nutrition cache columns
        print("Rebuilding Food nutrition cache columns from ingredients...")
        from domain.nutrition_compiler import compile_food_macros
        
        stmt_foods = select(Food).options(selectinload(Food.ingredient_associations).selectinload(FoodIngredient.ingredient))
        res_foods = await session.execute(stmt_foods)
        all_foods = res_foods.scalars().all()
        
        compiled_count = 0
        for f in all_foods:
            ingredients_list = []
            for assoc in f.ingredient_associations:
                ing = assoc.ingredient
                ingredients_list.append({
                    "base_macros": {
                        "caloriesKcal": ing.calories,
                        "proteinG": ing.protein,
                        "carbsG": ing.carbs,
                        "fatG": ing.fat,
                        "fiberG": ing.fiber
                    },
                    "quantity": assoc.quantity,
                    "unit": assoc.unit,
                    "default_unit": ing.default_unit,
                    "conversions": ing.conversions
                })
            
            macros = compile_food_macros(ingredients_list)
            f.calories = macros.get("caloriesKcal", 0.0)
            f.protein = macros.get("proteinG", 0.0)
            f.carbs = macros.get("carbsG", 0.0)
            f.fat = macros.get("fatG", 0.0)
            f.fiber = macros.get("fiberG", 0.0)
            compiled_count += 1
            if compiled_count % 200 == 0:
                await session.flush()
                
        print(f"Successfully compiled macros for {compiled_count} foods.")
        await session.commit()

        # 4.6 Recompile and Rebuild all Meal nutrition cache columns
        print("Rebuilding Meal nutrition cache columns from compiled foods...")
        from domain.meal_compiler import compile_meal_macros
        
        stmt_meals = select(Meal).options(selectinload(Meal.food_associations).selectinload(MealFood.food))
        res_meals = await session.execute(stmt_meals)
        all_meals = res_meals.scalars().all()
        
        compiled_meal_count = 0
        for m in all_meals:
            scaled_foods = []
            for assoc in m.food_associations:
                f = assoc.food
                base_qty = f.quantity
                scale = assoc.quantity / base_qty if base_qty > 0 else 1.0
                scaled_foods.append({
                    "macros": {
                        "caloriesKcal": f.calories * scale,
                        "proteinG": f.protein * scale,
                        "carbsG": f.carbs * scale,
                        "fatG": f.fat * scale,
                        "fiberG": f.fiber * scale
                    }
                })
            macros = compile_meal_macros(scaled_foods)
            m.calories = macros.get("caloriesKcal", 0.0)
            m.protein = macros.get("proteinG", 0.0)
            m.carbs = macros.get("carbsG", 0.0)
            m.fat = macros.get("fatG", 0.0)
            m.fiber = macros.get("fiberG", 0.0)
            compiled_meal_count += 1
            if compiled_meal_count % 100 == 0:
                await session.flush()
                
        print(f"Successfully compiled macros for {compiled_meal_count} meals.")
        await session.commit()


        # 5. User Preferences
        print("Importing preferences from memory...")
        pref_file = Path(__file__).resolve().parents[1] / "chat_memory" / "default_user.json"
        if pref_file.exists():
            try:
                prefs = json.loads(pref_file.read_text(encoding="utf-8"))
                stmt_pref = select(UserPreference).filter_by(user_identifier="default_user")
                res_pref = await session.execute(stmt_pref)
                pref_obj = res_pref.scalar_one_or_none()
                if not pref_obj:
                    pref_obj = UserPreference(
                        user_identifier="default_user",
                        likes=prefs.get("likes") or [],
                        dislikes=prefs.get("dislikes") or [],
                        allergies=prefs.get("allergies") or [],
                        notes=prefs.get("notes") or []
                    )
                    session.add(pref_obj)
                    await session.commit()
                    print("Seeded default user preferences successfully.")
            except Exception as e:
                print(f"Error seeding user preferences: {e}")

        # 6. Ingredient Substitutes (Reference Seed Data)
        print("Importing ingredient substitutes reference data...")
        subs_file = Path(__file__).resolve().parents[1] / "assets" / "nutrition" / "master_substituents.json"
        if not subs_file.exists():
            subs_file = Path(__file__).resolve().parents[2] / "migration_backup" / "original_json_datasets" / "master_substituents.json"
        if subs_file.exists():
            try:
                sub_data = json.loads(subs_file.read_text(encoding="utf-8"))
                seeded_subs_count = 0
                for item in sub_data:
                    sub_id = item.get("Subsitutes_ID")
                    allergen_name = item.get("allergen_name")
                    if not sub_id or not allergen_name:
                        continue
                    
                    # Check if already exists in DB
                    stmt_sub = select(Substitute).filter_by(allergen_name=allergen_name)
                    res_sub = await session.execute(stmt_sub)
                    sub_obj = res_sub.scalar_one_or_none()
                    if not sub_obj:
                        sub_obj = Substitute(
                            id=sub_id,
                            allergen_category=item.get("allergen_category"),
                            allergen_name=allergen_name,
                            substitutes=item.get("substitutes") or []
                        )
                        session.add(sub_obj)
                        seeded_subs_count += 1
                await session.commit()
                print(f"Seeded {seeded_subs_count} new ingredient substitutes successfully.")
            except Exception as e:
                print(f"Error seeding substitutes: {e}")

if __name__ == "__main__":
    asyncio.run(run_import())
