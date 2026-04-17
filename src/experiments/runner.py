import argparse
import json
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.experiments.report import write_csv, write_summary
from src.experiments.scoring import score_response
from src.experiments.storage import init_db, save_result


CURRENT_FILE = Path(__file__).resolve()
EXPERIMENTS_DIR = CURRENT_FILE.parent              # .../src/experiments
SRC_DIR = EXPERIMENTS_DIR.parent                   # .../src
PROJECT_ROOT = SRC_DIR.parent                      # .../workshop


def resolve_path(path_str: str, *, expect_dir: bool = False) -> Path:
    """
    Умеет искать путь в нескольких вариантах:
    1) как есть
    2) относительно корня проекта
    3) относительно src/
    4) относительно src/experiments/
    """
    raw = Path(path_str)

    candidates = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(raw)
        candidates.append(PROJECT_ROOT / raw)
        candidates.append(SRC_DIR / raw)
        candidates.append(EXPERIMENTS_DIR / raw)

    for candidate in candidates:
        if expect_dir and candidate.is_dir():
            return candidate
        if not expect_dir and candidate.is_file():
            return candidate

    checked = "\n".join(f"- {str(c)}" for c in candidates)
    kind = "directory" if expect_dir else "file"
    raise FileNotFoundError(
        f"Could not find {kind}: {path_str}\nChecked:\n{checked}"
    )


def load_dataset(dataset_path: str | Path) -> List[Dict[str, Any]]:
    dataset_file = resolve_path(str(dataset_path), expect_dir=False)
    return json.loads(dataset_file.read_text(encoding="utf-8"))


def load_configs(configs_dir: str | Path) -> List[Dict[str, Any]]:
    configs_path = resolve_path(str(configs_dir), expect_dir=True)

    configs: List[Dict[str, Any]] = []
    for file_path in sorted(configs_path.glob("*.json")):
        configs.append(json.loads(file_path.read_text(encoding="utf-8")))

    if not configs:
        raise FileNotFoundError(f"No config JSON files found in: {configs_path}")

    return configs


def _extract_response_text(response_json: Dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""

    first = choices[0] or {}
    message = first.get("message") or {}
    content = message.get("content")

    return content if isinstance(content, str) else ""


def _extract_trace_id(headers: Dict[str, str]) -> str | None:
    for key in ("x-trace-id", "trace-id", "x_trace_id"):
        if key in headers:
            return headers[key]
    return None


def call_chat_completion(
    *,
    base_url: str,
    model: str | None,
    prompt: str,
    runtime_params: Dict[str, Any],
    thread_id: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
        "thread_id": thread_id,
        "runtime_params": runtime_params,
    }

    if model:
        payload["model"] = model

    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            latency_ms = (time.perf_counter() - started) * 1000.0
            response_json = json.loads(body)
            headers = {k.lower(): v for k, v in response.headers.items()}

            return {
                "ok": True,
                "response_json": response_json,
                "response_text": _extract_response_text(response_json),
                "latency_ms": latency_ms,
                "trace_id": _extract_trace_id(headers),
                "headers": headers,
            }

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        latency_ms = (time.perf_counter() - started) * 1000.0

        return {
            "ok": False,
            "response_json": {"error": {"status": e.code, "body": body}},
            "response_text": body,
            "latency_ms": latency_ms,
            "trace_id": None,
            "headers": {},
        }

    except Exception as e:
        latency_ms = (time.perf_counter() - started) * 1000.0

        return {
            "ok": False,
            "response_json": {"error": {"type": e.__class__.__name__, "message": str(e)}},
            "response_text": str(e),
            "latency_ms": latency_ms,
            "trace_id": None,
            "headers": {},
        }


def run_experiment(
    *,
    dataset_path: str,
    configs_dir: str,
    base_url: str,
    default_model: str | None,
    db_path: str,
    output_dir: str,
    timeout_seconds: int,
) -> List[Dict[str, Any]]:
    dataset = load_dataset(dataset_path)
    configs = load_configs(configs_dir)

    experiment_run_id = uuid.uuid4().hex
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    db_file = PROJECT_ROOT / db_path if not Path(db_path).is_absolute() else Path(db_path)
    output = PROJECT_ROOT / output_dir if not Path(output_dir).is_absolute() else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    conn = init_db(db_file)

    results: List[Dict[str, Any]] = []

    for config in configs:
        config_name = config["name"]
        runtime_params = config.get("runtime_params", {})
        model = config.get("model") or default_model

        for case in dataset:
            test_id = case["id"]
            prompt = case["input"]
            thread_id = f"{experiment_run_id}:{config_name}:{test_id}"

            raw = call_chat_completion(
                base_url=base_url,
                model=model,
                prompt=prompt,
                runtime_params=runtime_params,
                thread_id=thread_id,
                timeout_seconds=timeout_seconds,
            )

            scoring = score_response(raw["response_text"], case.get("checks"))

            row = {
                "experiment_run_id": experiment_run_id,
                "test_id": test_id,
                "config_name": config_name,
                "input_text": prompt,
                "response_text": raw["response_text"],
                "score": scoring["score"],
                "passed": scoring["passed"],
                "latency_ms": raw["latency_ms"],
                "timestamp_utc": timestamp_utc,
                "thread_id": thread_id,
                "trace_id": raw.get("trace_id"),
                "runtime_params": runtime_params,
                "raw_response": raw["response_json"],
                "scoring": scoring,
            }

            save_result(conn, row)
            results.append(row)

            print(
                f"[{config_name}] {test_id}: "
                f"passed={row['passed']} score={row['score']:.4f} "
                f"latency={row['latency_ms']:.2f}ms"
            )

    write_csv(results, output / "results.csv")
    write_summary(results, output / "summary.md")

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run parameter experiments for workshop.")

    parser.add_argument(
        "--dataset",
        default="src/experiments/datasets/basic.json",
        help="Path to dataset JSON file.",
    )
    parser.add_argument(
        "--configs",
        default="src/experiments/configs",
        help="Path to directory with config JSON files.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Workshop base URL.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Default model name.",
    )
    parser.add_argument(
        "--db-path",
        default="src/experiments/results/results.sqlite3",
        help="SQLite output path.",
    )
    parser.add_argument(
        "--output-dir",
        default="src/experiments/results",
        help="Directory for reports.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="HTTP timeout.",
    )

    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    run_experiment(
        dataset_path=args.dataset,
        configs_dir=args.configs,
        base_url=args.base_url,
        default_model=args.model,
        db_path=args.db_path,
        output_dir=args.output_dir,
        timeout_seconds=args.timeout_seconds,
    )


if __name__ == "__main__":
    main()