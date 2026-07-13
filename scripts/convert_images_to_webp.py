import os
from PIL import Image

def convert_images(source_dir, target_dir):
    # Ensure target directory exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    supported_formats = ('.jpg', '.jpeg', '.png')
    count = 0

    for filename in os.listdir(source_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_formats:
            source_path = os.path.join(source_dir, filename)
            
            # Keep original filename but change extension to .webp
            new_filename = os.path.splitext(filename)[0] + '.webp'
            target_path = os.path.join(target_dir, new_filename)

            try:
                # Open image and convert to RGB if necessary (e.g. for PNG with transparency)
                with Image.open(source_path) as img:
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    # Save as webp
                    img.save(target_path, "webp", quality=85)
                print(f"Converted: {filename} -> {new_filename}")
                count += 1
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")

    print(f"\nSuccessfully converted {count} images.")

if __name__ == "__main__":
    src = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\north indian cuisine\fuzzy-images"
    dest = r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\north indian cuisine\images"
    convert_images(src, dest)
