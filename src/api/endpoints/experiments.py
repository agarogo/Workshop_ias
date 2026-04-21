import json
import uuid
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from src.api.experiment_schemas import (
    ConfigProfileCreate,
    ConfigProfileUpdate,
    ExperimentCatalogResponse,
    ExperimentJobStatus,
    ExperimentRunDetail,
    ExperimentRunInfo,
    ExperimentRunRequest,
    ExperimentRunResponse,
    TestCaseCreateRequest,
    TestCaseUpdateRequest,
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


def dataset_file_path(dataset: str) -> Path:
    raw = Path(dataset)
    if raw.is_absolute():
        return raw
    if str(raw).startswith("src/"):
        return PROJECT_ROOT / raw
    return datasets_root() / raw


def config_file_path(config_name: str) -> Path:
    safe_name = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return configs_root() / safe_name


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
        return []


def load_dataset_cases(dataset: str) -> List[Dict[str, Any]]:
    path = dataset_file_path(dataset)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_dataset_cases(dataset: str, cases: List[Dict[str, Any]]) -> None:
    path = dataset_file_path(dataset)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")


def load_config_payload(config_name: str) -> Dict[str, Any]:
    path = config_file_path(config_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found: {config_name}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_config_payload(config_name: str, payload: Dict[str, Any]) -> None:
    path = config_file_path(config_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
            selected_test_ids=body.selected_test_ids,
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


@router.get("/configs")
async def get_configs():
    result = []
    for name in list_config_files():
        result.append(load_config_payload(name))
    return result


@router.get("/configs/{config_name}")
async def get_config(config_name: str):
    return JSONResponse(content=load_config_payload(config_name))


@router.post("/configs")
async def create_config(body: ConfigProfileCreate):
    path = config_file_path(body.name)
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Config already exists: {body.name}")

    payload = body.model_dump(exclude_none=True)
    save_config_payload(body.name, payload)
    return JSONResponse(content=payload)


@router.put("/configs/{config_name}")
async def update_config(config_name: str, body: ConfigProfileUpdate):
    payload = load_config_payload(config_name)

    if body.model is not None:
        payload["model"] = body.model
    if body.runtime_params is not None:
        payload["runtime_params"] = body.runtime_params
    if body.description is not None:
        payload["description"] = body.description

    save_config_payload(config_name, payload)
    return JSONResponse(content=payload)


@router.delete("/configs/{config_name}")
async def delete_config(config_name: str):
    path = config_file_path(config_name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found: {config_name}")

    path.unlink()
    return {"deleted": True, "config_name": config_name}


@router.get("/tests")
async def get_tests(dataset: str = "src/experiments/datasets/basic.json"):
    return JSONResponse(content=load_dataset_cases(dataset))


@router.get("/tests/{test_id}")
async def get_test(test_id: str, dataset: str = "src/experiments/datasets/basic.json"):
    cases = load_dataset_cases(dataset)
    for case in cases:
        if case.get("id") == test_id:
            return JSONResponse(content=case)
    raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")


@router.post("/tests")
async def create_test(body: TestCaseCreateRequest):
    cases = load_dataset_cases(body.dataset)

    if any(case.get("id") == body.case.id for case in cases):
        raise HTTPException(status_code=409, detail=f"Test already exists: {body.case.id}")

    new_case = body.case.model_dump()
    cases.append(new_case)
    save_dataset_cases(body.dataset, cases)

    return JSONResponse(content=new_case)


@router.put("/tests/{test_id}")
async def update_test(test_id: str, body: TestCaseUpdateRequest):
    cases = load_dataset_cases(body.dataset)

    updated_case = None
    for case in cases:
        if case.get("id") == test_id:
            if body.input is not None:
                case["input"] = body.input
            if body.checks is not None:
                case["checks"] = body.checks
            if body.tags is not None:
                case["tags"] = body.tags
            updated_case = case
            break

    if updated_case is None:
        raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

    save_dataset_cases(body.dataset, cases)
    return JSONResponse(content=updated_case)


@router.delete("/tests/{test_id}")
async def delete_test(test_id: str, dataset: str = "src/experiments/datasets/basic.json"):
    cases = load_dataset_cases(dataset)
    filtered = [case for case in cases if case.get("id") != test_id]

    if len(filtered) == len(cases):
        raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")

    save_dataset_cases(dataset, filtered)
    return {"deleted": True, "test_id": test_id, "dataset": dataset}


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


@router.get("/runs/{run_id}/bundle")
async def get_run_bundle(run_id: str):
    run_dir = experiments_results_root() / run_id
    if not run_dir.exists() or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    manifest_path = run_dir / "run.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    bundle: Dict[str, Any] = {
        "run_id": run_id,
        "manifest": manifest,
        "configs": {},
    }

    for config_dir in sorted(run_dir.iterdir()):
        if config_dir.is_dir():
            config_payloads = []
            for json_file in sorted(config_dir.glob("*.json")):
                config_payloads.append(
                    json.loads(json_file.read_text(encoding="utf-8"))
                )
            bundle["configs"][config_dir.name] = config_payloads

    return JSONResponse(content=bundle)


@router.get("/runs/{run_id}/files/{config_name}/{file_name}")
async def get_run_test_file(run_id: str, config_name: str, file_name: str):
    file_path = experiments_results_root() / run_id / config_name / file_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Result file not found")

    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return JSONResponse(content=payload)