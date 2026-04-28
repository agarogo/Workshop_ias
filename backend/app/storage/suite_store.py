from typing import Any

from app.storage.json_store import delete_json, list_json_files, read_json, write_json
from app.storage.paths import suite_path, tests_suites_dir


def get_suite(suite_id: str) -> dict[str, Any] | None:
    return read_json(suite_path(suite_id))


def save_suite(payload: dict[str, Any]) -> None:
    write_json(suite_path(payload["id"]), payload)


def delete_suite(suite_id: str) -> None:
    delete_json(suite_path(suite_id))


def list_suites() -> list[dict[str, Any]]:
    return [read_json(path) for path in list_json_files(tests_suites_dir())]
