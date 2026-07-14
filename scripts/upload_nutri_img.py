import os
import boto3
from concurrent.futures import ThreadPoolExecutor, as_completed

BUCKET = "twellr-dev"
MAX_WORKERS = 10
EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif")

# Define mapping for directories
DIRECTORIES = [
    {
        "local_dir": r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\north indian cuisine\images",
        "s3_prefix": "nutri-analysis/images/north-indian/"
    },
    {
        "local_dir": r"d:\IAgami\Bioart Dataset\Diet Plan Updated\Diet-Plan-1\Diet-Plan\new core models\data\south indian cuisine\images",
        "s3_prefix": "nutri-analysis/images/south-indian/"
    }
]

s3 = boto3.client("s3")

def upload_file(filepath, key):
    try:
        # Check if we should add ContentType based on extension
        extra_args = {}
        if filepath.lower().endswith('.webp'):
            extra_args['ContentType'] = 'image/webp'
        s3.upload_file(filepath, BUCKET, key, ExtraArgs=extra_args)
        return (key, True, None)
    except Exception as e:
        return (key, False, str(e))

def main():
    tasks = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for entry in DIRECTORIES:
            local_dir = entry["local_dir"]
            s3_prefix = entry["s3_prefix"]
            
            if not os.path.exists(local_dir):
                print(f"[WARNING] Directory not found: {local_dir}")
                continue
                
            files = [
                f for f in os.listdir(local_dir)
                if f.lower().endswith(EXTENSIONS)
            ]
            print(f"Found {len(files)} images in {local_dir} to upload to {s3_prefix}")
            
            for fname in files:
                filepath = os.path.join(local_dir, fname)
                key = f"{s3_prefix}{fname}"
                tasks.append(executor.submit(upload_file, filepath, key))

        success, failed = 0, 0
        for future in as_completed(tasks):
            key, ok, err = future.result()
            if ok:
                success += 1
                print(f"[OK] {key}")
            else:
                failed += 1
                print(f"[FAIL] {key} - {err}")

    print(f"\nDone. Success: {success}, Failed: {failed}")

if __name__ == "__main__":
    main()