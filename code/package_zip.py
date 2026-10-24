import os
import zipfile
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
code_dir = root_dir / "code"
zip_path = root_dir / "code.zip"

if zip_path.exists():
    zip_path.unlink()

print(f"Creating {zip_path} from {code_dir}...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(code_dir):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for file in files:
            if file.endswith((".pyc", ".pyo")):
                continue
            file_path = Path(root) / file
            arcname = file_path.relative_to(root_dir)
            zipf.write(file_path, arcname)
            print(f"  Added: {arcname}")

print(f"Successfully packaged {zip_path} ({zip_path.stat().st_size} bytes)")

