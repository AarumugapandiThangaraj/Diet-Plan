import json
import os
import glob

# Search directory
SEARCH_DIR = os.path.join(os.path.dirname(__file__), "Data new", "Mealsdata")

def check_micronutrients():
    # We mainly care about foods.json and ingredients master.json?
    # The user asks if ALL the JSON files in Data new have Micronutrients.
    # Usually it's foods.json or ingredients.json.
    
    # Let's find all json files
    json_files = glob.glob(os.path.join(SEARCH_DIR, "**", "*.json"), recursive=True)
    
    report = {}
    
    for file in json_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # data could be a dict or a list of dicts
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = [data]
                
            total_items = len(items)
            items_with_micro = 0
            
            # Specifically check for foods or ingredients, some files might be 'meals.json' which don't have micronutrients.
            # But we'll just report the ratio of items with Micronutrients.
            for item in items:
                if isinstance(item, dict):
                    # Check if 'Micronutrients' key exists or 'Nutritional_Info' -> 'Micronutrients'
                    has_micro = False
                    if "Micronutrients" in item:
                        has_micro = True
                    elif "Nutritional_Info" in item and isinstance(item["Nutritional_Info"], dict) and "Micronutrients" in item["Nutritional_Info"]:
                        has_micro = True
                    
                    if has_micro:
                        items_with_micro += 1
            
            basename = os.path.relpath(file, SEARCH_DIR)
            report[basename] = {"total": total_items, "with_micro": items_with_micro}
            
        except Exception as e:
            print(f"Error reading {file}: {e}")

    # Print summary
    for filename, stats in report.items():
        # Only highlight if it's foods or ingredients
        if "foods.json" in filename.lower() or "ingredients" in filename.lower() or "meals" in filename.lower():
            total = stats["total"]
            with_m = stats["with_micro"]
            print(f"{filename}: {with_m} / {total} entries have Micronutrients")

if __name__ == '__main__':
    check_micronutrients()
