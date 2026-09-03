import shutil
from pathlib import Path

base_dir = Path(__file__).resolve().parent

pub_dir = base_dir / "src" / "dashboard" / "frontend" / "public"
dist_dir = base_dir / "src" / "dashboard" / "frontend" / "dist"

pub_dir.mkdir(parents=True, exist_ok=True)

logo_src = base_dir / "logo.png"
fav_src = base_dir / "favicon.png"

if logo_src.exists():
    shutil.copy(logo_src, pub_dir / "logo.png")
    if dist_dir.exists():
        shutil.copy(logo_src, dist_dir / "logo.png")

if fav_src.exists():
    shutil.copy(fav_src, pub_dir / "favicon.png")
    shutil.copy(fav_src, pub_dir / "favicon.ico")
    if dist_dir.exists():
        shutil.copy(fav_src, dist_dir / "favicon.png")
        shutil.copy(fav_src, dist_dir / "favicon.ico")

print("Copied logo and favicon to frontend public and dist directories successfully!")
