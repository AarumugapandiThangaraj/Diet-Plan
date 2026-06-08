import json
import os

META_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data new", "Images", "south_asia", "meta.json"))
IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data new", "Images", "south_asia", "images final"))
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "image_mapping.json")

def main():
    if not os.path.exists(META_FILE):
        print(f"Meta file not found: {META_FILE}")
        return
        
    with open(META_FILE, 'r', encoding='utf-8') as f:
        meta_data = json.load(f)
        
    actual_files = set(os.listdir(IMAGES_DIR))
    mapping = {}
    
    for food in meta_data:
        food_id = food.get("food_id")
        if not food_id:
            continue
            
        images = food.get("images", [])
        matched = False
        for img in images:
            local_path = img.get("local_saved_path", "")
            basename = os.path.basename(local_path)
            if basename in actual_files:
                mapping[food_id] = basename
                matched = True
                break
                
        if not matched:
            # Fallback if there's any file in images final matching the prefix (just in case)
            prefix = food.get("food_name", "").lower().replace(" ", "_")
            for actual in actual_files:
                if actual.startswith(prefix) and (actual.endswith(".jpg") or actual.endswith(".png") or actual.endswith(".webp")):
                    mapping[food_id] = actual
                    break

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2)
        
    print(f"Successfully created mapping for {len(mapping)} foods in {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
