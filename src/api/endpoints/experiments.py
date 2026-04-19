# src/api/endpoints/experiments.py
import json
import uuid
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from src.api.experiment_schemas import (
    ExperimentCatalogResponse,
    ExperimentJobStatus,
    ExperimentRunDetail,
    ExperimentRunInfo,
    ExperimentRunRequest,
    ExperimentRunResponse,
)
from src.config import settings
from src.experiments.runner import PROJECT_ROOT, run_experiment

router = APIRouter(prefix="/experiments", tags=["experiments"])

JOB_STORE: Dict[str, Dict[str, Any]] = {}


def experiments_results_root() -> Path:
    return PROJECT_ROOT / "src/experiments/results"


def datasets_root() -> Path:
    return PROJECT_ROOT / "src/experiments/datasets"


def configs_root() -> Path:
    return PROJECT_ROOT / "src/experiments/configs"


def list_dataset_files() -> List[str]:
    root = datasets_root()
    if not root.exists():
        return []
    return sorted(str(p.relative_to(PROJECT_ROOT)).replace("\\", "/") for p in root.glob("*.json"))


def list_config_files() -> List[str]:
    root = configs_root()
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def list_ollama_models() -> List[str]:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            models = payload.get("models", [])
            return sorted(
                {
                    item.get("name") or item.get("model")
                    for item in models
                    if item.get("name") or item.get("model")
                }
            )
    except Exception:
        # не роняем фронт, просто возвращаем пустой список
        return []


def _run_job(job_id: str, body: ExperimentRunRequest) -> None:
    try:
        JOB_STORE[job_id]["status"] = "running"

        selected_models = None
        if body.use_all_models:
            selected_models = list_ollama_models()
        elif body.selected_models:
            selected_models = body.selected_models

        result = run_experiment(
            dataset_path=body.dataset,
            configs_dir=body.configs_dir,
            base_url="http://localhost:8000",
            default_model=body.default_model,
            db_path=body.db_path,
            output_dir=body.output_dir,
            timeout_seconds=body.timeout_seconds,
            selected_config_names=body.selected_config_names,
            selected_models=selected_models,
        )

        JOB_STORE[job_id]["status"] = "completed"
        JOB_STORE[job_id]["experiment_run_id"] = result["experiment_run_id"]
        JOB_STORE[job_id]["result"] = result

    except Exception as e:
        JOB_STORE[job_id]["status"] = "failed"
        JOB_STORE[job_id]["error"] = f"{e.__class__.__name__}: {e}"


@router.get("/catalog", response_model=ExperimentCatalogResponse)
async def get_experiment_catalog():
    return ExperimentCatalogResponse(
        datasets=list_dataset_files(),
        configs=list_config_files(),
        models=list_ollama_models(),
    )


@router.post("/run", response_model=ExperimentRunResponse)
async def start_experiment_run(body: ExperimentRunRequest, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex
    JOB_STORE[job_id] = {
        "status": "queued",
        "experiment_run_id": None,
        "error": None,
        "result": None,
    }
    background_tasks.add_task(_run_job, job_id, body)
    return ExperimentRunResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=ExperimentJobStatus)
async def get_job_status(job_id: str):
    job = JOB_STORE.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ExperimentJobStatus(
        job_id=job_id,
        status=job["status"],
        experiment_run_id=job.get("experiment_run_id"),
        error=job.get("error"),
        result=job.get("result"),
    )


@router.get("/runs", response_model=List[ExperimentRunInfo])
async def list_runs():
    root = experiments_results_root()
    if not root.exists():
        return []

    runs: List[ExperimentRunInfo] = []
    for item in sorted(root.iterdir(), reverse=True):
        if item.is_dir():
            files = sorted(str(p.relative_to(item)).replace("\\", "/") for p in item.rglob("*.json"))
            runs.append(ExperimentRunInfo(run_id=item.name, files=files))
    return runs


@router.get("/runs/{run_id}", response_model=ExperimentRunDetail)
async def get_run_detail(run_id: str):
    run_dir = experiments_results_root() / run_id
    if not run_dir.exists() or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    manifest_path = run_dir / "run.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    configs: Dict[str, List[str]] = {}
    for item in sorted(run_dir.iterdir()):
        if item.is_dir():
            configs[item.name] = sorted(p.name for p in item.glob("*.json"))

    return ExperimentRunDetail(
        run_id=run_id,
        manifest=manifest,
        configs=configs,
    )


@router.get("/runs/{run_id}/files/{config_name}/{file_name}")
async def get_run_test_file(run_id: str, config_name: str, file_name: str):
    file_path = experiments_results_root() / run_id / config_name / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return JSONResponse(content=payload)