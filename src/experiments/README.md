
# experiments MVP

## Запуск

Из корня проекта:

```bash
python -m src.experiments.runner --base-url http://localhost:8000 --model qwen3:4b
```

```PowerShell
python -m src.experiments.runner --dataset src/experiments/datasets/basic.json --configs src/experiments/configs --base-url http://localhost:8000 --model qwen3:4b
```

## Что делает runner

- загружает датасет кейсов;
- загружает профили параметров;
- прогоняет каждый кейс на каждом профиле;
- считает deterministic score;
- сохраняет всё в SQLite;
- пишет `results.csv` и `summary.md`.

## Что уже проверяется

- точное совпадение;
- contains / not_contains;
- regex;
- валидность JSON;
- наличие обязательных ключей;
- ограничение длины ответа.
