import json
import re
import os

def update_json_file(filepath, cuisine_type):
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for m in data:
        m_id = str(m.get("meal_id", ""))
        match = re.search(r'\d+', m_id)
        
        if match:
            if cuisine_type == "north":
                img_filename = f"NI_MEAL_{match.group().zfill(3)}.webp"
                cuisine_folder = "north-indian"
            else:
                img_filename = f"SI_MEAL_{match.group().zfill(4)}.webp"
                cuisine_folder = "south-indian"
                
            m["image"] = f"https://d3k2cziv2oniyb.cloudfront.net/nutri-analysis/images/{cuisine_folder}/{img_filename}"
        else:
            m["image"] = ""
            
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    print(f"Successfully updated {len(data)} records in {filepath}")

if __name__ == "__main__":
    ni_file = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\north indian cuisine\meal.json"
    # si_file = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\south indian cuisine\meal.json"
    
    update_json_file(ni_file, "north")
    # update_json_file(si_file, "south")
