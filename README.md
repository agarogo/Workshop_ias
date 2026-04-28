# Workshop IAS + BenchFile

Репозиторий теперь собран как fullstack-приложение:

- `frontend/` — активный Next.js фронт с доской экспериментов.
- `backend/` — новый backend BenchFile/BenchMerge для хранения конфигов, тестов, suites, lineage и результатов прогонов.
- Старый workshop-orchestrator backend больше не используется в запуске проекта.

## Архитектура

```text
frontend Next.js
  -> /api/experiments/* Next proxy adapter
  -> backend BenchFile API
  -> storage/*.json
  -> PromptBench batch stream, если запускаются реальные прогоны
```

Фронт оставлен на старом удобном контракте `/api/experiments/*`, а Next.js proxy внутри `frontend/src/app/api/experiments/[...path]/route.ts` адаптирует его к новому API BenchFile.

## Структура проекта

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   └── schemas/
│   │   ├── core/
│   │   ├── services/
│   │   └── storage/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── package.json
│   └── .env.example
└── docker-compose.yml
```

## Быстрый запуск через Docker Compose

```bash
docker compose up --build
```

После запуска:

```text
Frontend: http://localhost:3000
Backend Swagger: http://localhost:8100/docs
Backend health: http://localhost:8100/health
```

## Локальный запуск без Docker

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100
```

На macOS/Linux активация venv:

```bash
source .venv/bin/activate
```

### 2. Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Фронт будет доступен на `http://localhost:3000`.

## ENV

### Backend

Backend читает переменные с префиксом `BENCHFILE_`:

```env
BENCHFILE_PROMPTBENCH_BASE_URL=http://localhost:8020
BENCHFILE_DEFAULT_MODEL=gemma3:4b
BENCHFILE_REQUEST_TIMEOUT_SECONDS=300
BENCHFILE_STORAGE_ROOT=storage
```

В Docker Compose используется volume `benchfile-storage`, поэтому JSON-хранилище не теряется после перезапуска контейнеров.

### Frontend

```env
NEXT_PUBLIC_EXPERIMENTS_API_URL=/api/experiments
EXPERIMENTS_BACKEND_URL=http://localhost:8100
```

В Docker Compose `EXPERIMENTS_BACKEND_URL` автоматически ставится как `http://backend:8100`.

## Основные backend endpoint'ы

### Health

```http
GET /health
```

### Configs

```http
GET /configs
GET /configs/{config_id}
POST /configs
PUT /configs/{config_id}
GET /configs/{config_id}/lineage
POST /configs/{config_id}/offspring
```

### Tests

```http
GET /tests
GET /tests/{test_id}
POST /tests
PUT /tests/{test_id}
DELETE /tests/{test_id}
```

### Suites

```http
GET /suites
GET /suites/{suite_id}
POST /suites
PUT /suites/{suite_id}
DELETE /suites/{suite_id}
```

### Runs

```http
GET /runs
POST /runs
GET /runs/{run_id}
POST /runs/select-best
```

### Files

```http
GET /files/tree
GET /files/json?path=views/configs_list.json
```

## Минимальные тестовые данные

Создать конфиг:

```bash
curl -X POST http://localhost:8100/configs ^
  -H "Content-Type: application/json" ^
  -d "{\"config_id\":\"cfg_0001\",\"name\":\"strict_gemma\",\"model\":\"gemma3:4b\",\"system_prompt\":\"Ты эксперт по Python.\",\"options\":{\"temperature\":0.2,\"top_k\":20,\"top_p\":0.9}}"
```

Создать тест:

```bash
curl -X POST http://localhost:8100/tests ^
  -H "Content-Type: application/json" ^
  -d "{\"test_id\":\"test_palindrome\",\"name\":\"Palindrome Python\",\"user_prompt\":\"Напиши функцию проверки палиндрома на Python\",\"checks\":{\"response_not_empty\":true,\"contains\":[\"def\",\"return\"]},\"tags\":[\"python\",\"algorithm\"]}"
```

Для PowerShell лучше использовать `Invoke-RestMethod` или одинарные кавычки вокруг JSON.

## Как фронт связан с backend

Фронт вызывает `experimentsApi` из `frontend/src/lib/api.ts`. По умолчанию он ходит в `/api/experiments`, а Next.js route-handler адаптирует запросы к BenchFile API:

```text
/api/experiments/catalog -> GET /configs + GET /tests
/api/experiments/tests -> GET/POST /tests
/api/experiments/runs -> GET /runs
/api/experiments/runs/{run_id} -> GET /runs/{run_id}
/api/experiments/run -> POST /runs
/api/experiments/files/* -> /files/*
```

## Примечание про старый backend

Старый LangGraph/workshop backend не участвует в `docker-compose.yml`. Новый активный backend находится только в `backend/`.
