"""
Mealsdata Validation & Ingestion Script
========================================
Two-pass validation then integration into the diet system.

Pass 1: JSON parse validity + schema structure
Pass 2: Cross-reference integrity (IDs, food refs, session normalization)
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

MEALSDATA_ROOT = Path(__file__).parent / "Data new" / "Mealsdata"
SHARED_INGREDIENTS = MEALSDATA_ROOT / "ingredients master.json"

# Map each region folder → (meals_file, foods_file, [optional ingredients_file])
REGION_MAP = {
    "african":       {"meals": "meals.json",                    "foods": "foods.json",              "ingredients": "ingredients.json"},
    "americas":      {"meals": "meals.json",                    "foods": "foods.json"},
    "continental":   {"meals": "filtered_meals_continental.json","foods": "foods.json"},
    "east_asia":     {"meals": "meals.json",                    "foods": "foods.json"},
    "fusion":        {"meals": "meals.json",                    "foods": None},   # Fusion has NO separate foods file
    "mediterranean": {"meals": "mediterranean_meals_M.json",    "foods": "mediterranean_foods_M.json"},
    "middle_east":   {"meals": "ME_meals_MD.json",              "foods": "ME_food_MD.json"},
    "nordic":        {"meals": "meals.json",                    "foods": "foods.json"},
    "oceania":       {"meals": "oceania_meals_O.json",          "foods": "oceania_foods_O.json"},
    "south_asia":    {"meals": "meals.json",                    "foods": "foods.json"},
    "southeast_asia":{"meals": "meals.json",                    "foods": "foods.json"},
    "central":       {"meals": "meals.json",                    "foods": "central_food1.json"},
    "russia":        {"meals": "meals.json",                    "foods": "foods.json"},
    "uae":           {"meals": "uae_meals.json",                "foods": "uae_foods.json"},
}

# Folder name → key mapping (actual folder names on disk)
FOLDER_TO_KEY = {
    "African": "african",
    "Americas": "americas",
    "Continental": "continental",
    "East Asia": "east_asia",
    "Fusion and global trends": "fusion",
    "Mediterranean": "mediterranean",
    "MiddleEast": "middle_east",
    "Nordic": "nordic",
    "Oceania": "oceania",
    "South Asia": "south_asia",
    "Southeast Asia": "southeast_asia",
    "central": "central",
    "russia": "russia",
    "uae": "uae",
}

# Required fields for a meal record
REQUIRED_MEAL_FIELDS = {"ID", "Name", "Session", "Foods"}
# Fusion uses different field names
FUSION_FIELD_MAP = {
    "Meal_ID": "ID",
    "Diet_Type": "Diet Type",
}

# Valid session values (must map to backend meal times)
VALID_SESSIONS = {
    "early morning", "breakfast", "mid morning", "mid-morning",
    "lunch", "dinner", "evening", "evening snack", "bedtime",
}


class ValidationReport:
    def __init__(self):
        self.results = {}  # region -> {status, errors, warnings, stats}
        self.global_meal_ids = {}  # meal_id -> region
        self.global_food_ids = {}  # food_id -> region
        
    def add_region(self, region, status, errors, warnings, stats):
        self.results[region] = {
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "stats": stats,
        }
    
    def print_report(self):
        print("\n" + "=" * 80)
        print("  MEALSDATA VALIDATION REPORT (DOUBLE-CHECK)")
        print("=" * 80)
        
        total_meals = 0
        total_foods = 0
        total_errors = 0
        total_warnings = 0
        
        for region, data in sorted(self.results.items()):
            status_icon = "✅" if data["status"] == "PASS" else ("⚠️" if data["status"] == "WARN" else "❌")
            stats = data["stats"]
            meals_count = stats.get("meals", 0)
            foods_count = stats.get("foods", 0)
            errors_count = len(data["errors"])
            warnings_count = len(data["warnings"])
            
            total_meals += meals_count
            total_foods += foods_count
            total_errors += errors_count
            total_warnings += warnings_count
            
            print(f"\n{status_icon} {region.upper()}")
            print(f"   Meals: {meals_count} | Foods: {foods_count}")
            
            if data["errors"]:
                for err in data["errors"][:5]:
                    print(f"   ❌ {err}")
                if len(data["errors"]) > 5:
                    print(f"   ... and {len(data['errors']) - 5} more errors")
                    
            if data["warnings"]:
                for warn in data["warnings"][:3]:
                    print(f"   ⚠️  {warn}")
                if len(data["warnings"]) > 3:
                    print(f"   ... and {len(data['warnings']) - 3} more warnings")
        
        # Check global ID collisions
        id_collisions = []
        seen = {}
        for mid, region in self.global_meal_ids.items():
            if mid in seen:
                id_collisions.append(f"Meal ID '{mid}' appears in both {seen[mid]} and {region}")
            seen[mid] = region
        
        print(f"\n{'=' * 80}")
        print(f"  SUMMARY")
        print(f"{'=' * 80}")
        print(f"  Total Regions: {len(self.results)}")
        print(f"  Total Meals:   {total_meals}")
        print(f"  Total Foods:   {total_foods}")
        print(f"  Total Errors:  {total_errors}")
        print(f"  Total Warnings:{total_warnings}")
        print(f"  ID Collisions: {len(id_collisions)}")
        
        if id_collisions:
            print(f"\n  ⚠️  CROSS-REGION ID COLLISIONS:")
            for col in id_collisions[:10]:
                print(f"     {col}")
        
        overall = "PASS ✅" if total_errors == 0 else "FAIL ❌"
        print(f"\n  Overall: {overall}")
        print("=" * 80)
        
        return total_errors == 0


def load_json(path):
    """Load and parse JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data, None
        if isinstance(data, dict):
            for key in ("foods", "meals", "ingredients"):
                if key in data and isinstance(data[key], list):
                    return data[key], None
            for v in data.values():
                if isinstance(v, list):
                    return v, None
        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"
    except Exception as e:
        return None, f"File read error: {e}"


def validate_meal_record(meal, region_key, report):
    """Validate a single meal record and return (is_valid, errors, warnings)."""
    errors = []
    warnings = []
    
    # Determine field names (handle Fusion's different schema)
    if region_key == "fusion":
        meal_id = meal.get("Meal_ID") or meal.get("ID") or ""
        name = meal.get("Name", "")
        session = meal.get("Session", "")
        foods = meal.get("Foods", [])
        diet_type = meal.get("Diet_Type") or meal.get("Diet Type", [])
        goal = meal.get("Goal", [])
    else:
        meal_id = meal.get("ID", "")
        name = meal.get("Name", "")
        session = meal.get("Session", "")
        foods = meal.get("Foods", [])
        diet_type = meal.get("Diet Type", [])
        goal = meal.get("Goal", [])
    
    # Check required fields
    if not meal_id:
        errors.append(f"Missing ID in meal: {name[:50] if name else 'Unknown'}")
    if not name:
        errors.append(f"Missing Name in meal: {meal_id}")
    if not session:
        errors.append(f"Missing Session in meal: {meal_id}")
    if not foods:
        errors.append(f"Missing/empty Foods in meal: {meal_id}")
    
    # Validate Session values
    if session:
        sessions = session if isinstance(session, list) else [session]
        for s in sessions:
            if s.strip().lower() not in VALID_SESSIONS:
                warnings.append(f"Unusual session '{s}' in meal {meal_id}")
    
    # Validate Foods structure
    if isinstance(foods, list):
        for i, food in enumerate(foods):
            if not isinstance(food, dict):
                errors.append(f"Food #{i} in {meal_id} is not a dict")
                continue
            if not food.get("ID"):
                errors.append(f"Food #{i} in {meal_id} missing ID")
            if food.get("Quantity") is None:
                warnings.append(f"Food #{i} in {meal_id} missing Quantity")
    
    # Check goal
    if not goal and region_key != "fusion":
        warnings.append(f"Missing Goal in meal {meal_id}")
    
    # Track meal ID globally for collision detection
    if meal_id:
        if meal_id in report.global_meal_ids:
            errors.append(f"Duplicate meal ID '{meal_id}' (also in {report.global_meal_ids[meal_id]})")
        report.global_meal_ids[meal_id] = region_key
    
    return len(errors) == 0, errors, warnings


def validate_food_record(food, region_key, report):
    """Validate a single food record."""
    errors = []
    warnings = []
    
    food_id = food.get("ID", "")
    name = food.get("Name", "")
    
    if not food_id:
        errors.append(f"Missing ID in food: {name[:50] if name else 'Unknown'}")
    if not name:
        warnings.append(f"Missing Name in food: {food_id}")
    
    if food_id:
        report.global_food_ids[food_id] = region_key
    
    return len(errors) == 0, errors, warnings


def validate_region(region_key, folder_name, report):
    """Validate all files for a region. Returns (status, errors, warnings, stats)."""
    config = REGION_MAP.get(region_key)
    if not config:
        return "SKIP", [f"No config for region {region_key}"], [], {}
    
    folder_path = MEALSDATA_ROOT / folder_name
    if not folder_path.exists():
        return "FAIL", [f"Folder not found: {folder_path}"], [], {}
    
    errors = []
    warnings = []
    stats = {}
    
    # ── Pass 1: Load and parse meals JSON ──
    meals_file = config.get("meals")
    if meals_file:
        meals_path = folder_path / meals_file
        if not meals_path.exists():
            errors.append(f"Meals file not found: {meals_path}")
            meals_data = []
        else:
            meals_data, parse_err = load_json(meals_path)
            if parse_err:
                errors.append(f"Meals file parse error: {parse_err}")
                meals_data = []
            elif not isinstance(meals_data, list):
                errors.append(f"Meals data is not a list (type: {type(meals_data).__name__})")
                meals_data = []
    else:
        meals_data = []
    
    stats["meals"] = len(meals_data)
    
    # ── Pass 1: Load and parse foods JSON ──
    foods_file = config.get("foods")
    if foods_file:
        foods_path = folder_path / foods_file
        if not foods_path.exists():
            errors.append(f"Foods file not found: {foods_path}")
            foods_data = []
        else:
            foods_data, parse_err = load_json(foods_path)
            if parse_err:
                errors.append(f"Foods file parse error: {parse_err}")
                foods_data = []
            elif not isinstance(foods_data, list):
                errors.append(f"Foods data is not a list (type: {type(foods_data).__name__})")
                foods_data = []
    else:
        foods_data = []
        warnings.append("No foods file configured for this region")
    
    stats["foods"] = len(foods_data)
    
    # ── Pass 2: Validate individual meal records ──
    valid_meals = 0
    for meal in meals_data:
        if not isinstance(meal, dict):
            errors.append(f"Non-dict meal record found")
            continue
        is_valid, merrs, mwarns = validate_meal_record(meal, region_key, report)
        errors.extend(merrs)
        warnings.extend(mwarns)
        if is_valid:
            valid_meals += 1
    
    stats["valid_meals"] = valid_meals
    
    # ── Pass 2: Validate individual food records ──
    valid_foods = 0
    food_ids_in_region = set()
    for food in foods_data:
        if not isinstance(food, dict):
            errors.append(f"Non-dict food record found")
            continue
        is_valid, ferrs, fwarns = validate_food_record(food, region_key, report)
        errors.extend(ferrs)
        warnings.extend(fwarns)
        if is_valid:
            valid_foods += 1
            food_ids_in_region.add(food.get("ID", ""))
    
    stats["valid_foods"] = valid_foods
    
    # ── Pass 2: Cross-reference food IDs in meals → foods ──
    if foods_data:  # Only check if we have a foods file
        missing_food_refs = set()
        for meal in meals_data:
            if not isinstance(meal, dict):
                continue
            for food_ref in meal.get("Foods", []):
                if not isinstance(food_ref, dict):
                    continue
                ref_id = food_ref.get("ID", "")
                if ref_id and ref_id not in food_ids_in_region:
                    missing_food_refs.add(ref_id)
        
        if missing_food_refs:
            warnings.append(f"{len(missing_food_refs)} food IDs referenced in meals but not found in foods file")
            # Show first few
            for ref in list(missing_food_refs)[:3]:
                warnings.append(f"  Missing food ref: {ref}")
    
    # Determine status
    if errors:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"
    
    return status, errors, warnings, stats


def run_full_validation():
    """Run complete two-pass validation across all regions."""
    report = ValidationReport()
    
    print("🔍 Starting Two-Pass Validation of Mealsdata...")
    print(f"   Root: {MEALSDATA_ROOT}")
    print()
    
    for folder_name, region_key in sorted(FOLDER_TO_KEY.items()):
        print(f"   Validating {folder_name}...", end=" ")
        status, errors, warnings, stats = validate_region(region_key, folder_name, report)
        report.add_region(region_key, status, errors, warnings, stats)
        icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
        print(f"{icon} ({stats.get('meals', 0)} meals, {stats.get('foods', 0)} foods)")
    
    passed = report.print_report()
    return passed, report


if __name__ == "__main__":
    passed, report = run_full_validation()
    sys.exit(0 if passed else 1)
