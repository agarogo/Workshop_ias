import json
import re
from typing import Any, Dict, List


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def score_response(response_text: str, checks: Dict[str, Any] | None) -> Dict[str, Any]:
    checks = checks or {}
    response_text = response_text or ""

    details: List[Dict[str, Any]] = []
    passed_count = 0
    total_count = 0

    def record(name: str, passed: bool, message: str = "") -> None:
        nonlocal passed_count, total_count
        total_count += 1
        if passed:
            passed_count += 1
        details.append(
            {
                "check": name,
                "passed": passed,
                "message": message,
            }
        )

    if checks.get("response_not_empty"):
        record(
            "response_not_empty",
            bool(response_text.strip()),
            "Ответ не должен быть пустым.",
        )

    if "equals" in checks:
        expected = str(checks["equals"])
        actual = response_text.strip()
        record(
            "equals",
            actual == expected,
            f"Ожидалось точное совпадение с {expected!r}.",
        )

    if "contains" in checks:
        for needle in _as_list(checks["contains"]):
            needle_str = str(needle)
            record(
                f"contains:{needle_str}",
                needle_str in response_text,
                f"Ответ должен содержать {needle_str!r}.",
            )

    if "not_contains" in checks:
        for needle in _as_list(checks["not_contains"]):
            needle_str = str(needle)
            record(
                f"not_contains:{needle_str}",
                needle_str not in response_text,
                f"Ответ не должен содержать {needle_str!r}.",
            )

    if "regex" in checks:
        for pattern in _as_list(checks["regex"]):
            matched = re.search(str(pattern), response_text, flags=re.MULTILINE) is not None
            record(
                f"regex:{pattern}",
                matched,
                f"Ответ должен соответствовать regex {pattern!r}.",
            )

    parsed_json = None
    if checks.get("json_valid") or "must_have_keys" in checks:
        parsed_json = _safe_json_loads(response_text)

    if checks.get("json_valid"):
        record(
            "json_valid",
            parsed_json is not None,
            "Ответ должен быть валидным JSON.",
        )

    if "must_have_keys" in checks:
        required_keys = _as_list(checks["must_have_keys"])
        is_dict = isinstance(parsed_json, dict)

        record(
            "json_is_object",
            is_dict,
            "JSON должен быть объектом.",
        )

        if is_dict:
            for key in required_keys:
                record(
                    f"must_have_key:{key}",
                    key in parsed_json,
                    f"JSON должен содержать ключ {key!r}.",
                )

    if "max_length" in checks:
        limit = int(checks["max_length"])
        actual_len = len(response_text)
        record(
            "max_length",
            actual_len <= limit,
            f"Длина ответа {actual_len}, лимит {limit}.",
        )

    if "min_length" in checks:
        limit = int(checks["min_length"])
        actual_len = len(response_text)
        record(
            "min_length",
            actual_len >= limit,
            f"Длина ответа {actual_len}, минимум {limit}.",
        )

    score = round((passed_count / total_count), 4) if total_count else 1.0
    passed = all(item["passed"] for item in details) if details else True

    return {
        "score": score,
        "passed": passed,
        "checks_total": total_count,
        "checks_passed": passed_count,
        "details": details,
    }