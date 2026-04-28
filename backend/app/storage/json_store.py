import json
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_json(path: Path) -> None:
    if path.exists():
        path.unlink()


def list_json_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(path.glob("*.json"))
