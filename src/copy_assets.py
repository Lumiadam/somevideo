import os
import shutil
import glob

BRAIN_DIR = r"C:\Users\User\AppData\Local\Temp" # Wait, the actual path is C:\Users\User\.gemini\antigravity\brain\dfb0e178-7fa0-4386-891e-b8c288234716
# Let's use the explicit absolute path provided in USER_REQUEST:
BRAIN_DIR = r"C:\Users\User\.gemini\antigravity\brain\dfb0e178-7fa0-4386-891e-b8c288234716"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

def copy_posters():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    
    mapping = {
        "interstellar_poster_*.png": "interstellar.png",
        "cyberpunk_poster_*.png": "cyberpunk.png",
        "romance_poster_*.png": "romance.png",
        "comedy_poster_*.png": "comedy.png",
        "thriller_poster_*.png": "thriller.png",
        "fantasy_poster_*.png": "fantasy.png"
    }
    
    print(f"Scanning for generated posters in: {BRAIN_DIR}")
    for pattern, target_name in mapping.items():
        search_path = os.path.join(BRAIN_DIR, pattern)
        matches = glob.glob(search_path)
        if matches:
            # Get the latest match
            matches.sort(key=os.path.getmtime)
            src_file = matches[-1]
            dest_file = os.path.join(ASSETS_DIR, target_name)
            shutil.copy2(src_file, dest_file)
            print(f"Copied {os.path.basename(src_file)} -> {dest_file}")
        else:
            print(f"No match found for pattern: {pattern}")

if __name__ == "__main__":
    copy_posters()
