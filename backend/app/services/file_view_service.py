from pathlib import Path

from fastapi import HTTPException

from app.core.settings import settings
from app.storage.json_store import read_json


def build_tree(root: Path, current: Path | None = None) -> dict:
    current = current or root
    node = {
        "name": current.name,
        "path": str(current.relative_to(root.parent)).replace('\\\\', '/'),
        "kind": "directory" if current.is_dir() else "file",
        "children": [],
    }
    if current.is_dir():
        for child in sorted(current.iterdir()):
            if child.name.startswith('.'):
                continue
            node["children"].append(build_tree(root, child))
    return node


def read_relative_json(relative_path: str) -> dict:
    full = settings.storage_root / relative_path
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {relative_path}")
    return read_json(full, {})
