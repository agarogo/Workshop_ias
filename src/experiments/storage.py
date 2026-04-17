import json
import sqlite3
from pathlib import Path
from typing import Any, Dict


SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS experiment_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_run_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    config_name TEXT NOT NULL,
    input_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    score REAL NOT NULL,
    passed INTEGER NOT NULL,
    latency_ms REAL NOT NULL,
    timestamp_utc TEXT NOT NULL,
    thread_id TEXT,
    trace_id TEXT,
    runtime_params_json TEXT NOT NULL,
    raw_response_json TEXT NOT NULL,
    scoring_json TEXT NOT NULL
);
'''


def init_db(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_SQL)
    conn.commit()
    return conn


def save_result(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    conn.execute(
        '''
        INSERT INTO experiment_results (
            experiment_run_id,
            test_id,
            config_name,
            input_text,
            response_text,
            score,
            passed,
            latency_ms,
            timestamp_utc,
            thread_id,
            trace_id,
            runtime_params_json,
            raw_response_json,
            scoring_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            row["experiment_run_id"],
            row["test_id"],
            row["config_name"],
            row["input_text"],
            row["response_text"],
            float(row["score"]),
            1 if row["passed"] else 0,
            float(row["latency_ms"]),
            row["timestamp_utc"],
            row.get("thread_id"),
            row.get("trace_id"),
            json.dumps(row.get("runtime_params", {}), ensure_ascii=False),
            json.dumps(row.get("raw_response", {}), ensure_ascii=False),
            json.dumps(row.get("scoring", {}), ensure_ascii=False),
        ),
    )
    conn.commit()