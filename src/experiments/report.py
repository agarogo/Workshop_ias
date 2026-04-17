from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List
import csv


def _group_by_config(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in results:
        grouped[row["config_name"]].append(row)
    return grouped


def write_csv(results: List[Dict[str, Any]], csv_path: str | Path) -> None:
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "experiment_run_id",
        "test_id",
        "config_name",
        "score",
        "passed",
        "latency_ms",
        "timestamp_utc",
        "thread_id",
        "trace_id",
        "input_text",
        "response_text",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_summary(results: List[Dict[str, Any]], summary_path: str | Path) -> None:
    summary_path = Path(summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    grouped = _group_by_config(results)

    lines: List[str] = []
    lines.append("# Experiment summary")
    lines.append("")

    if not results:
        lines.append("Нет результатов.")
        summary_path.write_text("\\n".join(lines), encoding="utf-8")
        return

    best_config = None
    best_avg_score = -1.0

    lines.append("## By config")
    lines.append("")
    lines.append("| Config | Cases | Pass rate | Avg score | Avg latency (ms) |")
    lines.append("|---|---:|---:|---:|---:|")

    for config_name, rows in grouped.items():
        total = len(rows)
        passed_count = sum(1 for row in rows if row["passed"])
        avg_score = sum(float(row["score"]) for row in rows) / total
        avg_latency = sum(float(row["latency_ms"]) for row in rows) / total

        if avg_score > best_avg_score:
            best_avg_score = avg_score
            best_config = config_name

        lines.append(
            f"| {config_name} | {total} | {passed_count / total:.2%} | "
            f"{avg_score:.4f} | {avg_latency:.2f} |"
        )

    lines.append("")
    lines.append(f"**Best config:** `{best_config}` with avg score **{best_avg_score:.4f}**")
    lines.append("")

    failed = [row for row in results if not row["passed"]]
    lines.append("## Failed cases")
    lines.append("")
    if not failed:
        lines.append("Все кейсы прошли.")
    else:
        for row in failed:
            lines.append(
                f"- `{row['config_name']}` / `{row['test_id']}` — "
                f"score={row['score']:.4f}, latency={row['latency_ms']:.2f} ms"
            )

    summary_path.write_text("\\n".join(lines), encoding="utf-8")