import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.storage.json_store import write_json
from app.storage.paths import test_results_view_path, tests_list_view_path
from app.storage.test_store import delete_test, get_test, list_tests, save_test


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def refresh_tests_view() -> None:
    tests = sorted(list_tests(), key=lambda x: (x.get("name", ""), x["id"]))
    write_json(tests_list_view_path(), {"items": tests})


def create_test(payload: dict) -> dict:
    test_id = payload.get("test_id") or _new_id("test")
    if get_test(test_id):
        raise HTTPException(status_code=409, detail=f"Test already exists: {test_id}")
    test = {
        "id": test_id,
        "name": payload["name"],
        "system_prompt": payload.get("system_prompt"),
        "user_prompt": payload["user_prompt"],
        "checks": payload.get("checks", {}),
        "tags": payload.get("tags", []),
        "created_at": _now(),
    }
    save_test(test)
    refresh_tests_view()
    write_json(test_results_view_path(test_id), {"test_id": test_id, "results": []})
    return test


def update_test(test_id: str, patch: dict) -> dict:
    test = get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")
    for field in ("name", "system_prompt", "user_prompt", "checks", "tags"):
        if field in patch and patch[field] is not None:
            test[field] = patch[field]
    test["updated_at"] = _now()
    save_test(test)
    refresh_tests_view()
    return test


def remove_test(test_id: str) -> None:
    if not get_test(test_id):
        raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")
    delete_test(test_id)
    refresh_tests_view()
