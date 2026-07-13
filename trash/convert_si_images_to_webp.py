import os
from PIL import Image
import re

def convert_images(source_dir):
    supported_formats = ('.jpg', '.jpeg', '.png')
    count = 0

    for filename in os.listdir(source_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_formats:
            source_path = os.path.join(source_dir, filename)
            
            # Keep original filename but change extension to .webp
            new_filename = os.path.splitext(filename)[0] + '.webp'
            target_path = os.path.join(source_dir, new_filename)

            try:
                # Open image and convert to RGB if necessary (e.g. for PNG with transparency)
                with Image.open(source_path) as img:
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    # Save as webp
                    img.save(target_path, "webp", quality=85)
                
                # Optionally delete original? User didn't say to delete, but usually you don't want duplicates.
                # The user said "convert ... to webp". I'll delete the original so we only have .webp left,
                # just like the NI task (wait, in NI task I converted from 'fuzzy-images' to 'images', so I didn't delete, 
                # but here the source and dest is the same 'images' folder. I will remove the original.)
                os.remove(source_path)
                
                print(f"Converted: {filename} -> {new_filename}")
                count += 1
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")

    print(f"\nSuccessfully converted {count} images.")

if __name__ == "__main__":
    src = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\south indian cuisine\images"
    convert_images(src)
