import os
import re

def rename_si_images(target_dir):
    count = 0
    for filename in os.listdir(target_dir):
        if filename.endswith(".webp"):
            # If it already matches SI_MEAL, skip
            if filename.startswith("SI_MEAL_"):
                continue
            
            # Extract number from M001
            match = re.search(r'\d+', filename)
            if match:
                num = match.group()
                # User asked for SI_MEAL_0001, so pad to 4 digits
                padded_num = num.zfill(4)
                new_filename = f"SI_MEAL_{padded_num}.webp"
                
                old_path = os.path.join(target_dir, filename)
                new_path = os.path.join(target_dir, new_filename)
                
                if not os.path.exists(new_path) and old_path != new_path:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {filename} -> {new_filename}")
                    count += 1
            else:
                print(f"Skipped {filename}: no numbers found")

    print(f"\nSuccessfully renamed {count} images.")

if __name__ == "__main__":
    dest = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\south indian cuisine\images"
    rename_si_images(dest)
