import os
import re
import shutil

def main():
    print("=== Nanco Asset Organizer ===")

    # 1. Create the assets directory
    assets_dir = "assets"
    os.makedirs(assets_dir, exist_ok=True)
    print(f"Directory '{assets_dir}/' created or already exists.")

    # 2. List of asset files in the root to move
    assets = [
        "HERO-PAINT.png",
        "Paint Workers Portal.jpg",
        "Why Humidity Matters.jpg",
        "calcbg.jpg",
        "catelog.jpg",
        "colors.jpg",
        "dark-logo.png",
        "house-bg.png",
        "house-bg1.png",
        "light-logo.png",
        "login-img.png",
        "outlet.png",
        "paint calculator.jpg",
        "paint visualizer.jpg",
        "pattern.jpg",
        "products.jpg",
        "sa.png",
        "visualizer bg.jpg"
    ]

    # 3. Move files to the assets directory
    moved_count = 0
    for asset in assets:
        if os.path.exists(asset):
            dest_path = os.path.join(assets_dir, asset)
            # If target already exists, remove it first to avoid collision
            if os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(asset, dest_path)
            print(f" -> Moved: {asset} to {dest_path}")
            moved_count += 1
        elif os.path.exists(os.path.join(assets_dir, asset)):
            print(f" -> Info: {asset} is already in {assets_dir}/")
        else:
            print(f" -> Warning: {asset} not found in root directory.")

    print(f"Moved {moved_count} assets.")

    # 4. Walk through files and update references
    extensions = [".html", ".css", ".js", ".json", ".py"]
    updated_files_count = 0

    def update_file_references(file_path):
        nonlocal updated_files_count
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # Skip binary/non-text files
            return
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return

        original_content = content
        
        for asset in assets:
            escaped_asset = re.escape(asset)
            
            # Match occurrences NOT already preceded by 'assets/' or 'assets\' or 'assets%2F'
            pattern = r'(?<!assets/)(?<!assets\\)(?<!assets%2F)\b' + escaped_asset + r'\b'
            content = re.sub(pattern, f"assets/{asset}", content, flags=re.IGNORECASE)
            
            # Also handle URL-encoded spaces (e.g. 'paint%20calculator.jpg')
            urlencoded_asset = asset.replace(" ", "%20")
            escaped_urlencoded = re.escape(urlencoded_asset)
            pattern_url = r'(?<!assets/)(?<!assets\\)(?<!assets%2F)\b' + escaped_urlencoded + r'\b'
            content = re.sub(pattern_url, f"assets/{urlencoded_asset}", content, flags=re.IGNORECASE)

        if content != original_content:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f" -> Updated references in: {file_path}")
                updated_files_count += 1
            except Exception as e:
                print(f"Error writing {file_path}: {e}")

    # Walk directories, excluding .git, assets, and python cache/venv folders
    exclude_dirs = {".git", "assets", "__pycache__", "venv", ".venv", "env", ".gemini"}
    for root, dirs, files in os.walk("."):
        # Prune excluded directories in-place to prevent walking them
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                # Skip the organizer script itself
                if file == "organize_assets.py":
                    continue
                file_path = os.path.join(root, file)
                update_file_references(file_path)

    print(f"Successfully updated references in {updated_files_count} files.")
    print("Asset organization is complete!")

if __name__ == "__main__":
    main()
