import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.services.promptbench_client import PromptBenchClient
from app.services.scoring import score_response
from app.storage.config_store import get_config
from app.storage.json_store import write_json
from app.storage.paths import config_results_view_path, leaderboard_view_path, result_path, runs_list_view_path, test_results_view_path
from app.storage.run_store import list_runs, run_bundle, save_result, save_run_index, save_run_manifest
from app.storage.suite_store import get_suite
from app.storage.test_store import get_test


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now_str() -> str:
    return _now_dt().isoformat()


def _new_run_id() -> str:
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def _new_result_id() -> str:
    return f"res_{uuid.uuid4().hex[:10]}"


def _extract_response_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    first = choices[0] or {}
    message = first.get("message") or {}
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _build_messages(config: dict, test: dict) -> list[dict[str, str]]:
    messages = []
    system_parts = [part for part in [config.get("system_prompt"), test.get("system_prompt")] if part]
    if system_parts:
        messages.append({"role": "system", "content": "\n\n".join(system_parts)})
    messages.append({"role": "user", "content": test["user_prompt"]})
    return messages


def refresh_runs_view() -> None:
    runs = sorted(list_runs(), key=lambda x: x.get("created_at", ""), reverse=True)
    write_json(runs_list_view_path(), {"items": runs})


def refresh_result_views(results: list[dict]) -> None:
    by_test = {}
    by_config = {}
    for result in results:
        by_test.setdefault(result["test_id"], []).append(result)
        by_config.setdefault(result["config_id"], []).append(result)
    for test_id, items in by_test.items():
        items_sorted = sorted(items, key=lambda x: (-float(x.get("score", 0.0)), float(x.get("latency_ms", 0.0))))
        write_json(test_results_view_path(test_id), {"test_id": test_id, "results": items_sorted})
        leaderboard = [
            {
                "config_id": i["config_id"],
                "config_name": i["config_name"],
                "score": i["score"],
                "latency_ms": i["latency_ms"],
                "result_id": i["id"],
                "run_id": i["run_id"],
            }
            for i in items_sorted
        ]
        write_json(leaderboard_view_path(test_id), {"test_id": test_id, "best_configs": leaderboard[:20]})
    for config_id, items in by_config.items():
        items_sorted = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
        write_json(config_results_view_path(config_id), {"config_id": config_id, "results": items_sorted})


def select_best_result(run_id: str, test_id: str, prefer_lower_latency: bool = True) -> dict:
    all_runs = list_runs()
    manifest = next((item for item in all_runs if item.get("run_id") == run_id), None)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    dt = datetime.fromisoformat(manifest["created_at"])
    bundle = run_bundle(run_id, dt)
    matches = [item for item in bundle["results"] if item.get("test_id") == test_id]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No results for test_id={test_id} in run_id={run_id}")
    matches.sort(key=lambda item: (-float(item.get("score", 0.0)), float(item.get("latency_ms", 0.0)) if prefer_lower_latency else 0.0))
    return matches[0]


async def create_run(suite_id: str | None, selected_test_ids: list[str] | None, config_ids: list[str], batch_stream_url: str | None = None) -> dict:
    if not config_ids:
        raise HTTPException(status_code=400, detail="config_ids must not be empty")
    if suite_id:
        suite = get_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")
        test_ids = suite.get("test_ids", [])
    else:
        test_ids = selected_test_ids or []
    if not test_ids:
        raise HTTPException(status_code=400, detail="Provide suite_id or selected_test_ids")

    tests = []
    for test_id in test_ids:
        test = get_test(test_id)
        if not test:
            raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")
        tests.append(test)

    configs = []
    for config_id in config_ids:
        config = get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
        configs.append(config)

    run_id = _new_run_id()
    now_dt = _now_dt()
    manifest = {
        "run_id": run_id,
        "created_at": now_dt.isoformat(),
        "suite_id": suite_id,
        "selected_test_ids": [t["id"] for t in tests],
        "selected_config_ids": [c["id"] for c in configs],
        "total_jobs": len(tests) * len(configs),
        "status": "running",
    }
    save_run_manifest(run_id, manifest, now_dt)

    batch_items = []
    id_map = {}
    next_id = 1
    for config in configs:
        for test in tests:
            payload = {
                "model": config.get("model"),
                "messages": _build_messages(config, test),
                "stream": False,
                "options": config.get("options", {}),
            }
            batch_items.append({"id": next_id, "payload": payload})
            id_map[next_id] = {"config": config, "test": test, "request_payload": payload}
            next_id += 1

    results = []
    index = {"run_id": run_id, "results": [], "by_config": {}, "by_test": {}}
    client = PromptBenchClient()

    async for event in client.stream_batch(batch_items, batch_stream_url=batch_stream_url):
        if "raw" in event:
            continue
        event_id = event.get("id")
        if event_id not in id_map:
            continue
        meta = id_map[event_id]
        config = meta["config"]
        test = meta["test"]
        response_payload = event.get("payload", {})
        response_text = _extract_response_text(response_payload)
        scoring = score_response(response_text, test.get("checks"))
        result_id = _new_result_id()
        result = {
            "id": result_id,
            "run_id": run_id,
            "config_id": config["id"],
            "config_name": config["name"],
            "test_id": test["id"],
            "test_name": test["name"],
            "family_id": config["family_id"],
            "generation": config.get("generation", 0),
            "model": config.get("model"),
            "request_payload": meta["request_payload"],
            "response_payload": response_payload,
            "response_text": response_text,
            "score": scoring["score"],
            "passed": scoring["passed"],
            "scoring": scoring,
            "latency_ms": 0.0,
            "created_at": _now_str(),
            "error": None,
        }
        save_result(run_id, result_id, result, now_dt)
        results.append(result)
        short = {
            "result_id": result_id,
            "config_id": result["config_id"],
            "config_name": result["config_name"],
            "test_id": result["test_id"],
            "test_name": result["test_name"],
            "score": result["score"],
            "passed": result["passed"],
            "latency_ms": result["latency_ms"],
            "file": str(result_path(run_id, result_id, now_dt)),
            "run_id": run_id,
        }
        index["results"].append(short)
        index["by_config"].setdefault(result["config_id"], []).append(result_id)
        index["by_test"].setdefault(result["test_id"], []).append(result_id)

    manifest["status"] = "completed"
    manifest["saved_results"] = len(results)
    save_run_manifest(run_id, manifest, now_dt)
    save_run_index(run_id, index, now_dt)
    refresh_runs_view()
    refresh_result_views(results)
    return {"run_id": run_id, "status": "completed", "saved_results": len(results)}
