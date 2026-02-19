# utils/file_utils.py
import hashlib
from pathlib import Path
import shutil

def get_file_sha256(path: Path):
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def safe_copy_file(source: Path, dest_dir: Path, rename_if_exists=True):
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source.name

    if dest_path.exists():
        source_hash = get_file_sha256(source)
        dest_hash = get_file_sha256(dest_path)
        if source_hash == dest_hash:
            return {"status": "skipped", "dest": dest_path}
        elif rename_if_exists:
            new_name = f"{source.stem}__{source.stat().st_mtime_ns}{source.suffix}"
            dest_path = dest_dir / new_name
            shutil.copy2(source, dest_path)
            return {"status": "copied_renamed", "dest": dest_path}
    shutil.copy2(source, dest_path)
    return {"status": "copied", "dest": dest_path}
