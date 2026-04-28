from typing import Any

from app.storage.json_store import delete_json, list_json_files, read_json, write_json
from app.storage.paths import config_item_path, configs_items_dir, family_path


def get_config(config_id: str) -> dict[str, Any] | None:
    return read_json(config_item_path(config_id))


def save_config(payload: dict[str, Any]) -> None:
    write_json(config_item_path(payload["id"]), payload)


def delete_config(config_id: str) -> None:
    delete_json(config_item_path(config_id))


def list_configs() -> list[dict[str, Any]]:
    return [read_json(path) for path in list_json_files(configs_items_dir())]


def get_family(family_id: str) -> dict[str, Any] | None:
    return read_json(family_path(family_id))


def save_family(payload: dict[str, Any]) -> None:
    write_json(family_path(payload["id"]), payload)
