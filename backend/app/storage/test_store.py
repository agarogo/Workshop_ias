from typing import Any

from app.storage.json_store import delete_json, list_json_files, read_json, write_json
from app.storage.paths import test_item_path, tests_items_dir


def get_test(test_id: str) -> dict[str, Any] | None:
    return read_json(test_item_path(test_id))


def save_test(payload: dict[str, Any]) -> None:
    write_json(test_item_path(payload["id"]), payload)


def delete_test(test_id: str) -> None:
    delete_json(test_item_path(test_id))


def list_tests() -> list[dict[str, Any]]:
    return [read_json(path) for path in list_json_files(tests_items_dir())]
