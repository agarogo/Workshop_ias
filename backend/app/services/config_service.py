import copy
import random
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.storage.config_store import get_config, get_family, list_configs, save_config, save_family
from app.storage.json_store import write_json
from app.storage.paths import configs_list_view_path, config_results_view_path, family_view_path
from app.storage.run_store import list_runs


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def refresh_configs_view() -> None:
    configs = sorted(list_configs(), key=lambda x: (x.get("name", ""), x["id"]))
    write_json(configs_list_view_path(), {"items": configs})


def refresh_family_view(family_id: str) -> None:
    family = get_family(family_id)
    if family:
        write_json(family_view_path(family_id), family)


def refresh_config_results_view(config_id: str) -> None:
    collected: list[dict[str, Any]] = []
    for run in list_runs():
        for result in run.get("index", {}).get("results", []):
            if result.get("config_id") == config_id:
                collected.append(result)
    write_json(config_results_view_path(config_id), {"config_id": config_id, "results": collected})


def create_config(payload: dict[str, Any]) -> dict[str, Any]:
    config_id = payload.get("config_id") or _new_id("cfg")
    if get_config(config_id):
        raise HTTPException(status_code=409, detail=f"Config already exists: {config_id}")
    family_id = _new_id("fam")
    config = {
        "id": config_id,
        "name": payload["name"],
        "family_id": family_id,
        "generation": 0,
        "parent_config_id": None,
        "model": payload.get("model", "gemma3:4b"),
        "system_prompt": payload.get("system_prompt"),
        "options": payload.get("options", {}),
        "description": payload.get("description"),
        "created_at": _now(),
        "lineage": None,
    }
    family = {"id": family_id, "root_config_id": config_id, "config_ids": [config_id], "edges": [], "created_at": _now()}
    save_config(config)
    save_family(family)
    refresh_configs_view()
    refresh_family_view(family_id)
    refresh_config_results_view(config_id)
    return config


def update_config(config_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    config = get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    for field in ("name", "model", "system_prompt", "options", "description"):
        if field in patch and patch[field] is not None:
            config[field] = patch[field]
    config["updated_at"] = _now()
    save_config(config)
    refresh_configs_view()
    refresh_family_view(config["family_id"])
    return config


def _mutate_value(key: str, value: Any) -> Any:
    if not isinstance(value, (int, float)):
        return value
    if key == "temperature":
        return round(max(0.0, min(2.0, float(value) + random.choice([-0.2, -0.1, 0.1, 0.2]))), 4)
    if key == "top_p":
        return round(max(0.1, min(1.0, float(value) + random.choice([-0.05, 0.05]))), 4)
    if key == "top_k":
        return max(1, int(value) + random.choice([-10, -5, 5, 10]))
    if key == "repeat_penalty":
        return round(max(0.5, min(2.0, float(value) + random.choice([-0.1, 0.1]))), 4)
    if key == "repeat_last_n":
        return max(1, int(value) + random.choice([-16, 16]))
    if key == "num_ctx":
        return max(256, int(value) + random.choice([-512, 512]))
    if key == "num_predict":
        return max(16, int(value) + random.choice([-64, 64]))
    return value


def create_offspring(config_id: str, count: int, name_prefix: str | None = None) -> list[dict[str, Any]]:
    parent = get_config(config_id)
    if not parent:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    family = get_family(parent["family_id"])
    if not family:
        raise HTTPException(status_code=404, detail=f"Family not found: {parent['family_id']}")
    created: list[dict[str, Any]] = []
    for idx in range(count):
        child_id = _new_id("cfg")
        child_options = copy.deepcopy(parent.get("options", {}))
        mutation_diff: dict[str, Any] = {}
        for key, old_value in list(child_options.items()):
            new_value = _mutate_value(key, old_value)
            if new_value != old_value:
                child_options[key] = new_value
                mutation_diff[key] = {"old": old_value, "new": new_value}
        child = {
            "id": child_id,
            "name": f"{name_prefix or parent['name']}_child_{idx + 1}",
            "family_id": parent["family_id"],
            "generation": int(parent.get("generation", 0)) + 1,
            "parent_config_id": parent["id"],
            "model": parent["model"],
            "system_prompt": parent.get("system_prompt"),
            "options": child_options,
            "description": f"Offspring of {parent['id']}",
            "created_at": _now(),
            "lineage": {"parent_config_id": parent["id"], "mutation_diff": mutation_diff, "selection_reason": "manual_offspring_creation"},
        }
        save_config(child)
        created.append(child)
        family.setdefault("config_ids", []).append(child_id)
        family.setdefault("edges", []).append({"parent": parent["id"], "child": child_id})
    save_family(family)
    refresh_configs_view()
    refresh_family_view(parent["family_id"])
    for child in created:
        refresh_config_results_view(child["id"])
    return created
