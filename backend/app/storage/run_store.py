from datetime import datetime
from typing import Any

from app.storage.json_store import read_json, write_json
from app.storage.paths import result_path, run_dir, run_index_path, run_manifest_path, run_results_dir, runs_root_dir


def save_run_manifest(run_id: str, payload: dict[str, Any], dt: datetime) -> None:
    write_json(run_manifest_path(run_id, dt), payload)


def save_run_index(run_id: str, payload: dict[str, Any], dt: datetime) -> None:
    write_json(run_index_path(run_id, dt), payload)


def save_result(run_id: str, result_id: str, payload: dict[str, Any], dt: datetime) -> None:
    write_json(result_path(run_id, result_id, dt), payload)


def run_bundle(run_id: str, dt: datetime) -> dict[str, Any]:
    manifest = read_json(run_manifest_path(run_id, dt), {})
    index = read_json(run_index_path(run_id, dt), {})
    results = []
    results_dir = run_results_dir(run_id, dt)
    if results_dir.exists():
        for item in sorted(results_dir.glob("*.json")):
            results.append(read_json(item))
    return {"run": manifest, "index": index, "results": results, "run_dir": str(run_dir(run_id, dt))}


def list_runs() -> list[dict[str, Any]]:
    root = runs_root_dir()
    if not root.exists():
        return []
    results: list[dict[str, Any]] = []
    for month_dir in sorted(root.iterdir(), reverse=True):
        if not month_dir.is_dir():
            continue
        for run_path in sorted(month_dir.iterdir(), reverse=True):
            if not run_path.is_dir():
                continue
            manifest = read_json(run_path / "run.json", {})
            if manifest:
                manifest = dict(manifest)
                manifest["index"] = read_json(run_path / "index.json", {})
                results.append(manifest)
    return results
