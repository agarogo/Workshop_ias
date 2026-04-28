from datetime import datetime, timezone
from pathlib import Path

from app.core.settings import settings


def storage_root() -> Path:
    return settings.storage_root


def configs_items_dir() -> Path:
    return storage_root() / "configs" / "items"


def configs_families_dir() -> Path:
    return storage_root() / "configs" / "families"


def tests_items_dir() -> Path:
    return storage_root() / "tests" / "items"


def tests_suites_dir() -> Path:
    return storage_root() / "tests" / "suites"


def runs_root_dir() -> Path:
    return storage_root() / "runs"


def views_root_dir() -> Path:
    return storage_root() / "views"


def views_leaderboard_dir() -> Path:
    return views_root_dir() / "leaderboard"


def views_config_results_dir() -> Path:
    return views_root_dir() / "config_results"


def views_test_results_dir() -> Path:
    return views_root_dir() / "test_results"


def views_families_dir() -> Path:
    return views_root_dir() / "families"


def config_item_path(config_id: str) -> Path:
    return configs_items_dir() / f"{config_id}.json"


def family_path(family_id: str) -> Path:
    return configs_families_dir() / f"{family_id}.json"


def test_item_path(test_id: str) -> Path:
    return tests_items_dir() / f"{test_id}.json"


def suite_path(suite_id: str) -> Path:
    return tests_suites_dir() / f"{suite_id}.json"


def run_month_dir(dt: datetime | None = None) -> Path:
    dt = dt or datetime.now(timezone.utc)
    return runs_root_dir() / dt.strftime("%Y-%m")


def run_dir(run_id: str, dt: datetime | None = None) -> Path:
    return run_month_dir(dt) / run_id


def run_manifest_path(run_id: str, dt: datetime | None = None) -> Path:
    return run_dir(run_id, dt) / "run.json"


def run_index_path(run_id: str, dt: datetime | None = None) -> Path:
    return run_dir(run_id, dt) / "index.json"


def run_results_dir(run_id: str, dt: datetime | None = None) -> Path:
    return run_dir(run_id, dt) / "results"


def result_path(run_id: str, result_id: str, dt: datetime | None = None) -> Path:
    return run_results_dir(run_id, dt) / f"{result_id}.json"


def configs_list_view_path() -> Path:
    return views_root_dir() / "configs_list.json"


def tests_list_view_path() -> Path:
    return views_root_dir() / "tests_list.json"


def suites_list_view_path() -> Path:
    return views_root_dir() / "suites_list.json"


def runs_list_view_path() -> Path:
    return views_root_dir() / "runs_list.json"


def leaderboard_view_path(test_id: str) -> Path:
    return views_leaderboard_dir() / f"{test_id}.json"


def config_results_view_path(config_id: str) -> Path:
    return views_config_results_dir() / f"{config_id}.json"


def test_results_view_path(test_id: str) -> Path:
    return views_test_results_dir() / f"{test_id}.json"


def family_view_path(family_id: str) -> Path:
    return views_families_dir() / f"{family_id}.json"
