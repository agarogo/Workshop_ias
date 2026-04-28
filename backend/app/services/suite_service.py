import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.storage.json_store import write_json
from app.storage.paths import suites_list_view_path
from app.storage.suite_store import delete_suite, get_suite, list_suites, save_suite
from app.storage.test_store import get_test


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def refresh_suites_view() -> None:
    suites = sorted(list_suites(), key=lambda x: (x.get("name", ""), x["id"]))
    write_json(suites_list_view_path(), {"items": suites})


def create_suite(payload: dict) -> dict:
    suite_id = payload.get("suite_id") or _new_id("suite")
    if get_suite(suite_id):
        raise HTTPException(status_code=409, detail=f"Suite already exists: {suite_id}")
    for test_id in payload.get("test_ids", []):
        if not get_test(test_id):
            raise HTTPException(status_code=404, detail=f"Unknown test_id in suite: {test_id}")
    suite = {
        "id": suite_id,
        "name": payload["name"],
        "description": payload.get("description"),
        "test_ids": payload.get("test_ids", []),
        "created_at": _now(),
    }
    save_suite(suite)
    refresh_suites_view()
    return suite


def update_suite(suite_id: str, patch: dict) -> dict:
    suite = get_suite(suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")
    if patch.get("test_ids") is not None:
        for test_id in patch["test_ids"]:
            if not get_test(test_id):
                raise HTTPException(status_code=404, detail=f"Unknown test_id in suite: {test_id}")
    for field in ("name", "description", "test_ids"):
        if field in patch and patch[field] is not None:
            suite[field] = patch[field]
    suite["updated_at"] = _now()
    save_suite(suite)
    refresh_suites_view()
    return suite


def remove_suite(suite_id: str) -> None:
    if not get_suite(suite_id):
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")
    delete_suite(suite_id)
    refresh_suites_view()
