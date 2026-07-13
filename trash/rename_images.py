import os
import re

def rename_images(target_dir):
    count = 0
    for filename in os.listdir(target_dir):
        if filename.endswith(".webp"):
            # If it already matches NI_MEAL_XXX, skip
            if filename.startswith("NI_MEAL_"):
                continue
            
            # If it's MEAL_XXX.webp, rename to NI_MEAL_XXX.webp
            # Or if it's just some other name, maybe the user wants them numbered? 
            # The prompt says "convert the images name... to NI_MEAL_XXX.webp"
            # Previous logs show they are named MEAL_001.webp etc.
            
            # Let's extract numbers if any
            match = re.search(r'\d+', filename)
            if match:
                num = match.group()
                # Ensure 3 digits
                padded_num = num.zfill(3)
                new_filename = f"NI_MEAL_{padded_num}.webp"
                
                old_path = os.path.join(target_dir, filename)
                new_path = os.path.join(target_dir, new_filename)
                
                # Check if target already exists to avoid overwriting
                if not os.path.exists(new_path) and old_path != new_path:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {filename} -> {new_filename}")
                    count += 1
                elif old_path != new_path:
                    print(f"Skipped {filename}: {new_filename} already exists")
            else:
                print(f"Skipped {filename}: no numbers found to format as XXX")

    print(f"\nSuccessfully renamed {count} images.")

if __name__ == "__main__":
    dest = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\north indian cuisine\images"
    rename_images(dest)
