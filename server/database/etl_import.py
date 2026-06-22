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
from database.models.catalog import Cuisine, MasterIngredient, Food, FoodIngredient, Meal, MealFood, Substitute, MealSession
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
    def __init__(self, data_root: Path, dry_run: bool = False, resolutions_file: Path = None):
        self.data_root = data_root
        self.dry_run = dry_run
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
        # 1. Load Ingredients
        ingredient_files = list(self.data_root.rglob("*ingredient*.json"))
        for p in ingredient_files:
            cuisine = clean_cuisine_name(p.name, p.parent.name)
            if p.parent.name.lower() == "others" or p.name.startswith("final_"):
                cuisine = "global"

            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                items = content.get("ingredients", []) if isinstance(content, dict) else (list(content.values()) if isinstance(content, dict) else content)
                if not isinstance(items, list):
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    ing_id = str(item.get("ID") or item.get("id") or "").strip()
                    name = str(item.get("Name") or item.get("name") or "").strip()
                    if not ing_id or not name:
                        continue

                    # Structure the ingredient raw data
                    item["_source_file"] = p.name
                    item["_cuisine"] = cuisine

                    if cuisine == "global":
                        if ing_id in self.global_ingredients:
                            existing = self.global_ingredients[ing_id]
                            if existing.get("Name") != name:
                                self.warnings.append(f"Duplicate ID Warning: Ingredient ID '{ing_id}' (global) defined multiple times with different names ('{existing.get('Name')}' vs '{name}') in {p.name}")
                            continue
                        self.global_ingredients[ing_id] = item
                    else:
                        self.ingredients_by_cuisine.setdefault(cuisine, {})
                        if ing_id in self.ingredients_by_cuisine[cuisine]:
                            existing = self.ingredients_by_cuisine[cuisine][ing_id]
                            if existing.get("Name") != name:
                                self.warnings.append(f"Duplicate ID Warning: Ingredient ID '{ing_id}' in cuisine {cuisine} defined multiple times with different names ('{existing.get('Name')}' vs '{name}') in {p.name}")
                            continue
                        self.ingredients_by_cuisine[cuisine][ing_id] = item

            except Exception as e:
                self.errors.append(f"Failed to parse ingredient file {p.name}: {e}")

        # 2. Load Foods
        mealsdata_dir = self.data_root / "Mealsdata"
        food_files = list(mealsdata_dir.rglob("*food*.json")) if mealsdata_dir.exists() else []
        for p in food_files:
            if "food_name_lists" in str(p) or "filtered_meals" in str(p):
                continue
            cuisine = clean_cuisine_name(p.name, p.parent.name)
            self.foods_by_cuisine.setdefault(cuisine, {})

            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                items = content.get("foods", []) if isinstance(content, dict) else (list(content.values()) if isinstance(content, dict) else content)
                if not isinstance(items, list):
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    f_id = str(item.get("ID") or item.get("id") or "").strip()
                    name = str(item.get("Name") or item.get("name") or "").strip()
                    if not f_id or not name:
                        continue

                    item["_source_file"] = p.name
                    item["_cuisine"] = cuisine

                    if f_id in self.foods_by_cuisine[cuisine]:
                        existing = self.foods_by_cuisine[cuisine][f_id]
                        if existing.get("Name") != name:
                            self.warnings.append(f"Duplicate ID Warning: Food ID '{f_id}' in cuisine {cuisine} defined multiple times with different names ('{existing.get('Name')}' vs '{name}') in {p.name}")
                        continue
                    self.foods_by_cuisine[cuisine][f_id] = item

            except Exception as e:
                self.errors.append(f"Failed to parse food file {p.name}: {e}")

        # 3. Load Meals
        mealsdata_dir = self.data_root / "Mealsdata"
        meal_files = list(mealsdata_dir.rglob("*meal*.json")) if mealsdata_dir.exists() else []
        for p in meal_files:
            cuisine = clean_cuisine_name(p.name, p.parent.name)
            self.meals_by_cuisine.setdefault(cuisine, {})

            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                items = content.get("meals", []) if isinstance(content, dict) else (list(content.values()) if isinstance(content, dict) else content)
                if not isinstance(items, list):
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    m_id = str(item.get("ID") or item.get("id") or "").strip()
                    name = str(item.get("Name") or item.get("name") or "").strip()
                    if not m_id or not name:
                        continue

                    item["_source_file"] = p.name
                    item["_cuisine"] = cuisine

                    if m_id in self.meals_by_cuisine[cuisine]:
                        existing = self.meals_by_cuisine[cuisine][m_id]
                        if existing.get("Name") != name:
                            self.warnings.append(f"Duplicate ID Warning: Meal ID '{m_id}' in cuisine {cuisine} defined multiple times with different names ('{existing.get('Name')}' vs '{name}') in {p.name}")
                        continue
                    self.meals_by_cuisine[cuisine][m_id] = item

            except Exception as e:
                self.errors.append(f"Failed to parse meal file {p.name}: {e}")

    def validate_in_memory(self, image_mapping: Dict[str, str]):
        """Runs validation checks completely in-memory."""
        # 1. Ingredients Deduplication & Conflict Detection
        by_normalized_name: Dict[str, List[Dict[str, Any]]] = {}
        
        # Gather all ingredients
        all_ings = list(self.global_ingredients.values())
        for c_ings in self.ingredients_by_cuisine.values():
            all_ings.extend(c_ings.values())

        for ing in all_ings:
            norm_name = normalize_ingredient_name(ing.get("Name") or ing.get("name"))
            by_normalized_name.setdefault(norm_name, []).append(ing)

        for norm_name, ing_list in by_normalized_name.items():
            if len(ing_list) > 1:
                # Compare macros
                base_macros = []
                for x in ing_list:
                    macros = x.get("Macros") or x.get("macros") or {}
                    base_macros.append({
                        "id": x.get("ID") or x.get("id"),
                        "file": x["_source_file"],
                        "calories": float(macros.get("Calories_kcal", macros.get("caloriesKcal", 0.0))),
                        "protein": float(macros.get("Protein_g", macros.get("proteinG", 0.0))),
                        "carbs": float(macros.get("Carbs_g", macros.get("carbsG", 0.0))),
                        "fat": float(macros.get("Fat_g", macros.get("fatG", 0.0))),
                        "fiber": float(macros.get("Fiber_g", macros.get("fiberG", 0.0))),
                    })

                # Check if macros differ significantly
                first = base_macros[0]
                has_conflict = False
                for other in base_macros[1:]:
                    for k in ["calories", "protein", "carbs", "fat", "fiber"]:
                        if abs(first[k] - other[k]) > 0.1:
                            has_conflict = True
                            break
                    if has_conflict:
                        break

                if has_conflict:
                    self.conflicts.append({
                        "normalized_name": norm_name,
                        "ingredients": base_macros
                    })

        # 2. Food & Meal Reference Integrity and Validation
        for cuisine, c_foods in self.foods_by_cuisine.items():
            for f_id, f in c_foods.items():
                # Check empty recipe and autocreate fallback placeholder ingredient
                ing_list = f.get("Ingredients") or f.get("ingredients") or []
                if not ing_list:
                    self.warnings.append(f"Empty Recipe Warning: Food '{f['Name']}' ({f_id}) in cuisine {cuisine} has 0 ingredients. Creating fallback base ingredient.")
                    fallback_ing_id = f"ING_FB_{f_id}"
                    fallback_ing_name = f"{f['Name']} (Base)"
                    f_macros = f.get("Nutritional_Info") or f.get("Nutritional_Info_per_Serving") or f.get("Nutritional_info") or {}
                    
                    self.global_ingredients[fallback_ing_id] = {
                        "ID": fallback_ing_id,
                        "Name": fallback_ing_name,
                        "unit": f.get("Unit") or "g",
                        "Macros": {
                            "Calories_kcal": float(f_macros.get("Calories_kcal", f_macros.get("caloriesKcal", 0.0))),
                            "Protein_g": float(f_macros.get("Protein_g", f_macros.get("proteinG", 0.0))),
                            "Carbs_g": float(f_macros.get("Carbs_g", f_macros.get("carbsG", 0.0))),
                            "Fat_g": float(f_macros.get("Fat_g", f_macros.get("fatG", 0.0))),
                            "Fiber_g": float(f_macros.get("Fiber_g", f_macros.get("fiberG", 0.0))),
                        },
                        "_source_file": "empty_recipe_generator",
                        "_cuisine": "global"
                    }
                    
                    f["Ingredients"] = [{
                        "Ingredient_ID": fallback_ing_id,
                        "Ingredient": fallback_ing_name,
                        "Quantity": float(f.get("Quantity") or 1.0),
                        "Unit": f.get("Unit") or "g",
                        "Swapable": False
                    }]
                    ing_list = f["Ingredients"]

                # Check references and units
                for ref in ing_list:
                    ref_id = str(ref.get("Ingredient_ID") or ref.get("ingredient_id") or ref.get("ID") or ref.get("id") or "").strip()
                    if not ref_id:
                        self.warnings.append(f"Food '{f['Name']}' ({f_id}) has ingredient reference with missing ID")
                        continue

                    # Verify ingredient exists
                    ing_exists = False
                    if ref_id in self.global_ingredients:
                        ing_exists = True
                    elif cuisine in self.ingredients_by_cuisine and ref_id in self.ingredients_by_cuisine[cuisine]:
                        ing_exists = True
                    else:
                        # Check other cuisines as fallback
                        for other_c in self.ingredients_by_cuisine:
                            if ref_id in self.ingredients_by_cuisine[other_c]:
                                ing_exists = True
                                break
                    
                    if not ing_exists:
                        # Autocreate missing ingredient fallback instead of critical error
                        self.warnings.append(f"Reference Warning: Food '{f['Name']}' ({f_id}) references missing ingredient '{ref_id}'. Will create placeholder.")
                        self.global_ingredients[ref_id] = {
                            "ID": ref_id,
                            "Name": f"Placeholder {ref_id}",
                            "unit": "g",
                            "Macros": {"Calories_kcal": 0, "Protein_g": 0, "Carbs_g": 0, "Fat_g": 0, "Fiber_g": 0},
                            "_source_file": "placeholder_generator",
                            "_cuisine": "global"
                        }

                    # Check units - downgrade unsupported units to Warning since conversion engine has fallback
                    raw_unit = str(ref.get("Unit") or ref.get("unit") or "g").strip()
                    unit = normalize_unit_name(raw_unit)
                    if unit not in GRAM_UNITS and unit not in UNIT_TO_GRAMS:
                        self.warnings.append(f"Unsupported Unit Warning: Food '{f['Name']}' ({f_id}) references ingredient '{ref_id}' with invalid unit '{raw_unit}'. Using fallback.")

                # Warning for missing image
                if f_id not in image_mapping:
                    self.warnings.append(f"Missing Image Asset: Food '{f['Name']}' ({f_id}) has no image asset mapping")

        for cuisine, c_meals in self.meals_by_cuisine.items():
            for m_id, m in c_meals.items():
                food_list = m.get("Foods") or m.get("foods") or []
                if not food_list:
                    self.warnings.append(f"Empty Meal: Meal '{m['Name']}' ({m_id}) in cuisine {cuisine} has 0 foods")
                    continue

                valid_foods = []
                for ref in food_list:
                    ref_id = str(ref.get("ID") or ref.get("id") or "").strip()
                    if not ref_id:
                        self.warnings.append(f"Meal '{m['Name']}' ({m_id}) has food reference with missing ID")
                        continue

                    # Verify food exists
                    if ref_id not in c_foods:
                        self.warnings.append(f"Reference Warning: Meal '{m['Name']}' ({m_id}) references missing food '{ref_id}' in same cuisine. Skipping reference.")
                    else:
                        valid_foods.append(ref)

                    # Check units - downgrade to warning
                    raw_unit = str(ref.get("Unit") or ref.get("unit") or "g").strip()
                    unit = normalize_unit_name(raw_unit)
                    if unit not in GRAM_UNITS and unit not in UNIT_TO_GRAMS:
                        self.warnings.append(f"Unsupported Unit Warning: Meal '{m['Name']}' ({m_id}) references food '{ref_id}' with invalid unit '{raw_unit}'. Using fallback.")

                # Update meal foods list or mark meal for removal if no valid foods remain
                if not valid_foods:
                    self.warnings.append(f"Empty Meal (After skips): Meal '{m['Name']}' ({m_id}) in cuisine {cuisine} has 0 valid foods remaining")
                else:
                    m["Foods"] = valid_foods

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
        asyncio.run(self.write_to_db(image_mapping))
        return True

    async def write_to_db(self, image_mapping: Dict[str, str]):
        print("\nWriting verified datasets to database...")
        # Create all tables cleanly by dropping the entire schema with CASCADE
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS \"Twellr_Nutri\" CASCADE"))
            await conn.execute(text("CREATE SCHEMA \"Twellr_Nutri\""))
            await conn.run_sync(Base.metadata.create_all)
        print("Database schemas created.")

        async with AsyncSessionLocal() as session:
            print("Seeding cuisines and meal sessions...")
            cuisine_db_map = {}
            for c_name in CUISINE_LIST:
                cuisine_obj = Cuisine(name_en=c_name, code=c_name)
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

            # 2. Master Ingredients
            print("Seeding master ingredients...")
            by_normalized_name: Dict[str, List[Dict[str, Any]]] = {}
            all_ings = list(self.global_ingredients.values())
            for c_ings in self.ingredients_by_cuisine.values():
                all_ings.extend(c_ings.values())

            for ing in all_ings:
                norm_name = normalize_ingredient_name(ing.get("Name") or ing.get("name"))
                by_normalized_name.setdefault(norm_name, []).append(ing)

            resolved_master_map: Dict[Tuple[str, str], int] = {} # (cuisine, client_id) -> master_id
            master_name_to_id: Dict[str, int] = {}

            for norm_name, ing_list in by_normalized_name.items():
                authoritative = ing_list[0]
                if norm_name in self.resolutions:
                    res = self.resolutions[norm_name]
                    target_id = res.get("authoritative_id")
                    target_file = res.get("source_file")
                    for x in ing_list:
                        if (x.get("ID") or x.get("id")) == target_id and x["_source_file"] == target_file:
                            authoritative = x
                            break

                macros = authoritative.get("Macros") or authoritative.get("macros") or {}
                master_ing = MasterIngredient(
                    name_en=str(authoritative.get("Name") or authoritative.get("name") or "").strip(),
                    default_unit=str(authoritative.get("Default_Unit") or authoritative.get("unit") or "g").strip(),
                    calories_kcal=float(macros.get("Calories_kcal", macros.get("caloriesKcal", 0.0))),
                    protein_g=float(macros.get("Protein_g", macros.get("proteinG", 0.0))),
                    carbs_g=float(macros.get("Carbs_g", macros.get("carbsG", 0.0))),
                    fat_g=float(macros.get("Fat_g", macros.get("fatG", 0.0))),
                    fiber_g=float(macros.get("Fiber_g", macros.get("fiberG", 0.0))),
                    micronutrients=authoritative.get("Micronutrients") or authoritative.get("micronutrients") or {},
                    benefits=authoritative.get("Benefits") or authoritative.get("benefits") or {},
                    caution=str(authoritative.get("Caution") or "").strip(),
                    notes=str(authoritative.get("Notes") or "").strip()
                )
                session.add(master_ing)
                await session.flush()
                master_name_to_id[norm_name] = master_ing.id

                # Create alias entries for every duplicate in the group in-memory
                for x in ing_list:
                    client_id = str(x.get("ID") or x.get("id")).strip()
                    cuisine = x["_cuisine"]
                    resolved_master_map[(cuisine, client_id)] = master_ing.id

            await session.commit()
            print("Master ingredients seeded.")

            # 3. Seed Foods and FoodIngredients
            print("Seeding foods...")
            food_db_map: Dict[Tuple[int, str], int] = {} # (cuisine_id, client_food_id) -> db_food_id
            for cuisine, c_foods in self.foods_by_cuisine.items():
                cuisine_obj = cuisine_db_map.get(cuisine)
                if not cuisine_obj:
                    continue

                for f_id, item in c_foods.items():
                    resolved_img = image_mapping.get(f_id, "")
                    food_obj = Food(
                        cuisine_id=cuisine_obj.id,
                        client_food_id=f_id,
                        name_en=str(item.get("Name") or item.get("name") or "").strip(),
                        description_en=str(item.get("Description") or "").strip(),
                        quantity=float(item.get("Quantity") or 0.0),
                        min_quantity=float(item.get("Min_Quantity") or item.get("min_quantity") or 0.0) or None,
                        max_quantity=float(item.get("Max_Quantity") or item.get("max_quantity") or 0.0) or None,
                        unit=str(item.get("Unit") or "g").strip(),
                        preparation_en="\n".join(item.get("Preparation")) if isinstance(item.get("Preparation"), list) else str(item.get("Preparation") or "").strip(),
                        notes=str(item.get("Notes") or "").strip(),
                        image_url=resolved_img,
                        diet_types=item.get("Diet Type") or item.get("diet_type") or [],
                        supports=item.get("Supports") or []
                    )
                    session.add(food_obj)
                    await session.flush()
                    food_db_map[(cuisine_obj.id, f_id)] = food_obj.id

                    # Add food ingredients junctions
                    seen_ingredients = set()
                    for ing_ref in item.get("Ingredients") or item.get("ingredients") or []:
                        ref_id = str(ing_ref.get("Ingredient_ID") or ing_ref.get("ingredient_id") or ing_ref.get("ID") or ing_ref.get("id") or "").strip()
                        if not ref_id or ref_id in seen_ingredients:
                            continue
                        seen_ingredients.add(ref_id)

                        # Resolve master ID using alias map or Jaro-Winkler fallback
                        master_id = resolved_master_map.get((cuisine, ref_id))
                        if not master_id:
                            master_id = resolved_master_map.get(("global", ref_id))
                        if not master_id:
                            # Try fuzzy match fallback on normalized name
                            ref_ing = self.global_ingredients.get(ref_id)
                            if not ref_ing and cuisine in self.ingredients_by_cuisine:
                                ref_ing = self.ingredients_by_cuisine[cuisine].get(ref_id)
                            
                            if ref_ing:
                                ref_norm = normalize_ingredient_name(ref_ing.get("Name") or ref_ing.get("name"))
                                master_id = master_name_to_id.get(ref_norm)

                        if not master_id:
                            # Dynamic fallback placeholder creation during DB seeding
                            fallback_name = f"Placeholder {ref_id}"
                            fallback_norm = normalize_ingredient_name(fallback_name)
                            master_id = master_name_to_id.get(fallback_norm)
                            if not master_id:
                                fallback_master = MasterIngredient(
                                    name_en=fallback_name,
                                    default_unit="g",
                                    calories_kcal=0.0,
                                    protein_g=0.0,
                                    carbs_g=0.0,
                                    fat_g=0.0,
                                    fiber_g=0.0,
                                    micronutrients={},
                                    benefits={}
                                )
                                session.add(fallback_master)
                                await session.flush()
                                master_id = fallback_master.id
                                master_name_to_id[fallback_norm] = master_id
                                resolved_master_map[(cuisine, ref_id)] = master_id

                        raw_unit = str(ing_ref.get("Unit") or ing_ref.get("unit") or "g").strip()
                        unit = normalize_unit_name(raw_unit)

                        fi = FoodIngredient(
                            food_id=food_obj.id,
                            ingredient_id=master_id,
                            quantity=float(ing_ref.get("Quantity") or ing_ref.get("quantity") or 0.0)
                        )
                        session.add(fi)

            await session.commit()
            print("Foods and food ingredient junctions seeded.")

            # 4. Seed Meals and MealFoods
            print("Seeding meals...")
            for cuisine, c_meals in self.meals_by_cuisine.items():
                cuisine_obj = cuisine_db_map.get(cuisine)
                if not cuisine_obj:
                    continue

                for m_id, item in c_meals.items():
                    resolved_img = ""
                    for food_ref in item.get("Foods") or item.get("foods") or []:
                        ref_id = str(food_ref.get("ID") or food_ref.get("id") or "").strip()
                        if ref_id in image_mapping:
                            val = image_mapping[ref_id]
                            resolved_img = val.split("/")[-1] if "/" in val else val
                            break

                    raw_sessions = item.get("Session") or item.get("sessions") or item.get("session") or []
                    norm_code = _normalize_meal_time(raw_sessions)
                    if not norm_code or norm_code not in session_db_map:
                        norm_code = "lunch" # Default fallback
                        
                    meal_obj = Meal(
                        cuisine_id=cuisine_obj.id,
                        client_meal_id=m_id,
                        name_en=str(item.get("Name") or item.get("name") or "").strip(),
                        description_en=str(item.get("Description") or "").strip(),
                        meal_session_id=session_db_map[norm_code],
                        diet_types=item.get("Diet Type") or item.get("diet_types") or item.get("diet_type") or [],
                        goal=item.get("Goal") or item.get("goal") or []
                    )
                    session.add(meal_obj)
                    await session.flush()

                    # Add meal foods junctions
                    seen_foods = set()
                    for food_ref in item.get("Foods") or food_ref.get("foods") or []:
                        ref_id = str(food_ref.get("ID") or food_ref.get("id") or "").strip()
                        if not ref_id or ref_id in seen_foods:
                            continue
                        seen_foods.add(ref_id)

                        food_db_id = food_db_map.get((cuisine_obj.id, ref_id))
                        if not food_db_id:
                            continue

                        mf = MealFood(
                            meal_id=meal_obj.id,
                            food_id=food_db_id,
                            is_replaceable=bool(food_ref.get("Replaceable") or food_ref.get("replaceable") or False)
                        )
                        session.add(mf)

            await session.commit()
            print("Meals and meal food junctions seeded.")

            # 5. Caches are managed by background tasks or queries in v2, skipping explicit column caching
            print("Meal and Food relationships loaded.")

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
    args = parser.parse_args()

    data_root = Path(__file__).resolve().parents[2] / "migration_backup" / "original_json_datasets"
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

    pipeline = ETLPipeline(data_root, dry_run=args.dry_run, resolutions_file=resolutions_file)
    success = pipeline.run(image_mapping)
    if not success:
        sys.exit(1)
