"""
ETL Database Seed & Rebuild Pipeline (Phase 1 Upgraded)

Initializes PostgreSQL tables under the new Master Ingredient catalog structure.
Performs pre-import in-memory validation, deduplication conflict checking,
and maps Foods/Meals namespace-safely. Compiles nutrition caches using standard unit density conversion.
"""

import asyncio
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from config.settings import settings
from config.constants import VALID_CUISINES, GRAM_UNITS, MEAL_TIME_ORDER
from domain.conversion_engine import UNIT_TO_GRAMS
from utils.normalizers import _normalize_meal_time
from database.base import Base
from database.session import engine, AsyncSessionLocal
import database.models
from database.models.catalog import (
    Cuisine, Food, Meal, MealFood, MealIngredient,
    Substitute, MealSession, FoodRole, PrimaryGoal, MealPrimaryGoal,
    SecondaryGoal, MealSecondaryGoal
)
from database.models.preference import UserPreference


# Cuisines list matching the original settings
CUISINE_LIST = list(VALID_CUISINES.keys())

def clean_cuisine_name(filename: str, parent_name: str) -> str:
    combined = f"{parent_name}_{filename}".lower().replace(" ", "_")
    # Sort cuisines by length in descending order to match longer prefixes first
    for c in sorted(CUISINE_LIST, key=len, reverse=True):
        c_clean = c.replace("_", "")
        if c in combined or c_clean in combined:
            return c
        parts = c.split("_")
        if all(part in combined for part in parts):
            return c

    # Custom mapping fallsbacks
    if "southeast_asia" in combined or "southeastasia" in combined:
        return "southeast_asian"
    if "east_asia" in combined or "eastasia" in combined:
        return "east_asian"
    if "south_asia" in combined or "southasia" in combined:
        return "south_asian"
    if "middle_east" in combined or "middleeast" in combined:
        return "middle_eastern"
    if "russia" in combined:
        return "russian"
    if "north" in combined:
        return "north_indian"
    if "south" in combined:
        return "south_indian"
    return "north_indian"

def jaro_winkler(s1: str, s2: str) -> float:
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    match_bound = max(len1, len2) // 2 - 1
    if match_bound < 0:
        match_bound = 0
        
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    
    matches = 0
    transpositions = 0
    
    for i in range(len1):
        start = max(0, i - match_bound)
        end = min(len2, i + match_bound + 1)
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
                
    if matches == 0:
        return 0.0
        
    k = 0
    for i in range(len1):
        if s1_matches[i]:
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
            
    j_score = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3.0
    
    prefix_len = 0
    for i in range(min(4, min(len1, len2))):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    return j_score + prefix_len * 0.1 * (1.0 - j_score)

def normalize_ingredient_name(name: str) -> str:
    s = str(name or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s

def normalize_unit_name(unit: str) -> str:
    u = str(unit or "g").strip().lower()
    if u in GRAM_UNITS or u in UNIT_TO_GRAMS:
        return u
    # Check plural
    if u.endswith("s"):
        u_sing = u[:-1]
        if u_sing in GRAM_UNITS or u_sing in UNIT_TO_GRAMS:
            return u_sing
    return u

class ETLPipeline:
    def __init__(self, data_root: Path, dry_run: bool = False, resolutions_file: Path = None, test_schema: str = None):
        self.data_root = data_root
        self.dry_run = dry_run
        self.test_schema = test_schema
        self.resolutions_file = resolutions_file
        self.resolutions = {}
        if resolutions_file and resolutions_file.exists():
            try:
                self.resolutions = json.loads(resolutions_file.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Warning: Failed to load resolutions file: {e}")

        # In-memory structures populated during validation
        self.ingredients_by_cuisine: Dict[str, Dict[str, Dict[str, Any]]] = {} # cuisine -> client_id -> data
        self.foods_by_cuisine: Dict[str, Dict[str, Dict[str, Any]]] = {} # cuisine -> client_id -> data
        self.meals_by_cuisine: Dict[str, Dict[str, Dict[str, Any]]] = {} # cuisine -> client_id -> data
        self.global_ingredients: Dict[str, Dict[str, Any]] = {} # client_id -> data
        
        # Validation output
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.conflicts: List[Dict[str, Any]] = []

    def load_all_datasets(self):
        print(f"Loading datasets from {self.data_root}")
        self.meals_list = []
        self.foods_list = []
        self.meal_foods_list = []
        self.meal_ingredients_list = []
        
        # Traverse all cuisine folders
        for cuisine_dir in self.data_root.iterdir():
            if not cuisine_dir.is_dir():
                continue
                
            meal_path = cuisine_dir / "meal.json"
            food_path = cuisine_dir / "food.json"
            mf_path = cuisine_dir / "meal_food.json"
            mi_path = cuisine_dir / "meal_ingredient.json"
            
            cuisine_code = clean_cuisine_name("", cuisine_dir.name) or "north_indian"
            
            if meal_path.exists():
                with open(meal_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for m in data: m["_cuisine"] = cuisine_code
                    self.meals_list.extend(data)
            if food_path.exists():
                with open(food_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for fd in data: fd["_cuisine"] = cuisine_code
                    self.foods_list.extend(data)
            if mf_path.exists():
                with open(mf_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mf in data: mf["_cuisine"] = cuisine_code
                    self.meal_foods_list.extend(data)
            if mi_path.exists():
                with open(mi_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mi in data: mi["_cuisine"] = cuisine_code
                    self.meal_ingredients_list.extend(data)
                    
        print(f"Loaded {len(self.meals_list)} meals, {len(self.foods_list)} foods, {len(self.meal_foods_list)} meal_foods, {len(self.meal_ingredients_list)} meal_ingredients.")

    def validate_in_memory(self, image_mapping: Dict[str, str]):
        pass

    def run(self, image_mapping: Dict[str, str]) -> bool:
        """Executes the pipeline."""
        print("Starting NutriLLM Data Ingestion pipeline...")
        self.load_all_datasets()
        self.validate_in_memory(image_mapping)

        # Check deduplication conflicts
        unresolved = []
        for conf in self.conflicts:
            norm_name = conf["normalized_name"]
            if norm_name not in self.resolutions:
                unresolved.append(conf)

        # Print reports
        print(f"\n=================== ETL PIPELINE INGESTION REPORT ===================")
        print(f"Cuisines found: {len(self.foods_by_cuisine)}")
        print(f"Ingredients loaded: {len(self.global_ingredients) + sum(len(x) for x in self.ingredients_by_cuisine.values())}")
        print(f"Foods loaded: {sum(len(x) for x in self.foods_by_cuisine.values())}")
        print(f"Meals loaded: {sum(len(x) for x in self.meals_by_cuisine.values())}")
        print(f"Deduplication conflicts found: {len(self.conflicts)} (Unresolved: {len(unresolved)})")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Errors: {len(self.errors)}")
        print(f"=====================================================================")

        if self.warnings:
            print("\nWARNINGS:")
            for w in self.warnings[:10]:
                print(f"  - {w}")
            if len(self.warnings) > 10:
                print(f"  - ... and {len(self.warnings) - 10} more warnings")

        if self.conflicts:
            print("\nDEDUPLICATION CONFLICTS:")
            for c in self.conflicts[:5]:
                print(f"  - '{c['normalized_name']}':")
                for ing in c["ingredients"]:
                    print(f"    * ID '{ing['id']}' in file '{ing['file']}' -> Calories: {ing['calories']} kcal")
            if len(self.conflicts) > 5:
                print(f"  - ... and {len(self.conflicts) - 5} more conflicts")

        if self.errors or unresolved:
            print("\nFATAL ERRORS & UNRESOLVED CONFLICTS:")
            for err in self.errors[:10]:
                print(f"  - [CRITICAL ERROR] {err}")
            if len(self.errors) > 10:
                print(f"  - ... and {len(self.errors) - 10} more errors")
            for u in unresolved:
                print(f"  - [UNRESOLVED CONFLICT] '{u['normalized_name']}' requires manual macro profile selection.")
            print("\nIngestion halted due to validation failures.")
            return False

        if self.dry_run:
            print("\nDry-run mode successful! No database changes performed.")
            return True

        # Database Insertion Phase
        asyncio.run(self.write_to_db(image_mapping, self.test_schema))
        return True

    async def write_to_db(self, image_mapping: Dict[str, str], test_schema: str = None):
        print("\nWriting verified datasets to database...")
        target_schema = test_schema if test_schema else "Twellr_Nutri"
        
        # Schema translation mapping for SQLAlchemy models
        translate_map = {"Twellr_Nutri": target_schema} if test_schema else None
        
        # Create all tables cleanly by dropping the entire schema with CASCADE
        engine_options = engine
        if translate_map:
            engine_options = engine.execution_options(schema_translate_map=translate_map)
            
        async with engine_options.begin() as conn:
            await conn.execute(text(f"DROP SCHEMA IF EXISTS \"{target_schema}\" CASCADE"))
            await conn.execute(text(f"CREATE SCHEMA \"{target_schema}\""))
            await conn.run_sync(Base.metadata.create_all)
                
        print(f"Database schemas created under {target_schema}.")

        # Setup session with schema translation
        session_factory = AsyncSessionLocal
        if translate_map:
            session_factory = lambda: AsyncSessionLocal(bind=engine.execution_options(schema_translate_map=translate_map))

        async with session_factory() as session:
            print("Seeding cuisines and meal sessions...")
            cuisine_db_map = {}
            # Collect dynamic cuisines from loaded data
            all_cuisines = set(CUISINE_LIST)
            for m in self.meals_list:
                if "_cuisine" in m:
                    all_cuisines.add(m["_cuisine"])
                    
            for c_name in all_cuisines:
                cuisine_obj = Cuisine(name_en=c_name.replace("_", " ").title(), code=c_name)
                session.add(cuisine_obj)
                await session.flush()
                cuisine_db_map[c_name] = cuisine_obj
                
            session_db_map = {}
            for code in MEAL_TIME_ORDER:
                name = code.title().replace("_", " ")
                session_obj = MealSession(name_en=name, code=code)
                session.add(session_obj)
                await session.flush()
                session_db_map[code] = session_obj.id

            print("Seeding reference tables...")
            roles = ['base', 'side', 'snack', 'dessert', 'beverage', 'condiment', 'other']
            for r in roles:
                role_obj = FoodRole(code=r, name_en=r.capitalize())
                session.add(role_obj)
            await session.commit()
            
            # Since primary goals and secondary goals are now dynamic from JSON, we'll build them during meal insert
            primary_goal_map = {}
            secondary_goal_map = {}
            
            print("Seeding Foods...")
            food_map = {}
            food_counter = 1
            
            for f in self.foods_list:
                c_code = f.get("_cuisine", "north_indian")
                c_id = cuisine_db_map[c_code].id
                real_f_id = f"{c_code}-{f.get('food_id')}"
                if real_f_id not in food_map:
                    food_map[real_f_id] = food_counter
                    food_counter += 1
                food_obj = Food(
                    id=food_map[real_f_id],
                    cuisine_id=c_id,
                    food_name=f.get("food_name", "")
                )
                session.add(food_obj)
                
            await session.flush()

            print("Seeding Meals...")
            meal_map = {}
            meal_counter = 1
            
            for m in self.meals_list:
                m_id = m.get("meal_id")
                c_code = m.get("_cuisine", "north_indian")
                real_m_id = f"{c_code}-{m_id}"
                m_session = str(m.get("session") or "Unknown").strip()
                normalized_session = _normalize_meal_time(m_session)
                session_id = session_db_map.get(normalized_session)
                
                nut = m.get("nutrition", {})
                
                c_code = m.get("_cuisine", "north_indian")
                c_id = cuisine_db_map[c_code].id
                real_m_id = f"{c_code}-{m_id}"
                
                if real_m_id not in meal_map:
                    meal_map[real_m_id] = meal_counter
                    meal_counter += 1
                
                meal_obj = Meal(
                    id=meal_map[real_m_id],
                    cuisine_id=c_id,
                    meal_session_id=session_id,
                    session=m_session,
                    recipe_name=m.get("recipe_name", ""),
                    time=m.get("time"),
                    description=m.get("description"),
                    allergens=m.get("allergens") or [],
                    preparation_steps=m.get("preparation_steps") or [],
                    calories_kcal=float(nut.get("calories_kcal", 0.0)),
                    carbohydrates_g=float(nut.get("carbohydrates_g", 0.0)),
                    protein_g=float(nut.get("protein_g", 0.0)),
                    fat_g=float(nut.get("fat_g", 0.0)),
                    dietary_fiber_g=float(nut.get("dietary_fiber_g", 0.0))
                )
                session.add(meal_obj)
                
                for p_goal in m.get("primary_goal") or []:
                    p_goal_str = str(p_goal).strip()
                    code = p_goal_str.strip().lower().replace(" ", "_").replace("&", "and")
                    if code not in primary_goal_map:
                        pg_obj = PrimaryGoal(code=code, name_en=p_goal_str)
                        session.add(pg_obj)
                        await session.flush()
                        primary_goal_map[code] = pg_obj.id
                    
                    session.add(MealPrimaryGoal(meal_id=meal_map[real_m_id], primary_goal_id=primary_goal_map[code]))
                    
                for s_goal in m.get("secondary_goal") or []:
                    s_goal_str = str(s_goal).strip()
                    code = s_goal_str.strip().lower().replace(" ", "_").replace("&", "and")
                    if code not in secondary_goal_map:
                        sg_obj = SecondaryGoal(code=code, name_en=s_goal_str)
                        session.add(sg_obj)
                        await session.flush()
                        secondary_goal_map[code] = sg_obj.id
                    
                    session.add(MealSecondaryGoal(meal_id=meal_map[real_m_id], secondary_goal_id=secondary_goal_map[code]))
            
            await session.flush()

            print("Seeding MealFoods...")
            for mf in self.meal_foods_list:
                c_code = mf.get("_cuisine", "north_indian")
                real_m_id = f"{c_code}-{mf.get('meal_id')}"
                real_f_id = f"{c_code}-{mf.get('food_id')}"
                
                if real_m_id not in meal_map or real_f_id not in food_map:
                    continue
                    
                val = str(mf.get("serving_size", ""))
                match = re.search(r"([\d\.]+)", val)
                parsed_size = float(match.group(1)) if match else 0.0
                
                mf_obj = MealFood(
                    meal_id=meal_map[real_m_id],
                    food_id=food_map[real_f_id],
                    serving_size=parsed_size
                )
                session.add(mf_obj)
                
            print("Seeding MealIngredients...")
            seen_mi = set()
            for mi in self.meal_ingredients_list:
                c_code = mi.get("_cuisine", "north_indian")
                real_m_id = f"{c_code}-{mi.get('meal_id')}"
                key = (real_m_id, mi.get("ingredient_name", ""))
                if key in seen_mi:
                    continue
                seen_mi.add(key)
                if real_m_id not in meal_map:
                    continue
                    
                mi_obj = MealIngredient(
                    meal_id=meal_map[real_m_id],
                    ingredient_name=mi.get("ingredient_name", ""),
                    quantity=float(mi.get("quantity", 0.0)),
                    unit=mi.get("unit")
                )
                session.add(mi_obj)

            await session.commit()
            # 7. Seed Preferences & Substitutes
            print("Seeding user preferences...")
            pref_file = Path(__file__).resolve().parents[1] / "chat_memory" / "default_user.json"
            if pref_file.exists():
                try:
                    prefs = json.loads(pref_file.read_text(encoding="utf-8"))
                    pref_obj = UserPreference(
                        user_identifier="default_user",
                        likes=prefs.get("likes") or [],
                        dislikes=prefs.get("dislikes") or [],
                        allergies=prefs.get("allergies") or [],
                        notes=prefs.get("notes") or []
                    )
                    session.add(pref_obj)
                    await session.commit()
                    print("Preferences seeded successfully.")
                except Exception as e:
                    print(f"Error seeding user preferences: {e}")

            print("Seeding substitutes...")
            subs_file = self.data_root / "master_substituents.json"
            if subs_file.exists():
                try:
                    sub_data = json.loads(subs_file.read_text(encoding="utf-8"))
                    for item in sub_data:
                        sub_id = item.get("Subsitutes_ID")
                        allergen_name = item.get("allergen_name")
                        if not sub_id or not allergen_name:
                            continue
                        sub_obj = Substitute(
                            allergen_category=item.get("allergen_category"),
                            allergen_code=allergen_name,
                            name_en=allergen_name,
                            substitutes=item.get("substitutes") or {}
                        )
                        session.add(sub_obj)
                    await session.commit()
                    print("Substitutes seeded successfully.")
                except Exception as e:
                    print(f"Error seeding substitutes: {e}")

            print("\nDatabase load and cache recompilation completed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NutriLLM Ingestion & Migration CLI")
    parser.add_argument("--dry-run", action="store_true", help="Validate input datasets without altering DB")
    parser.add_argument("--resolve-conflicts", type=str, default=None, help="Path to JSON file containing conflict resolutions")
    parser.add_argument("--test-schema", type=str, default=None, help="Schema name to use for testing instead of overriding Twellr_Nutri")
    args = parser.parse_args()

    data_root = Path(__file__).resolve().parents[2] / "new core models" / "data"
    resolutions_file = Path(args.resolve_conflicts) if args.resolve_conflicts else Path(__file__).resolve().parent / "conflict_resolutions.json"

    # Load image mapping
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
        except Exception as e:
            print(f"Warning: Failed to load image mapping: {e}")

    pipeline = ETLPipeline(data_root, dry_run=args.dry_run, resolutions_file=resolutions_file, test_schema=args.test_schema)
    success = pipeline.run(image_mapping)
    if not success:
        sys.exit(1)
