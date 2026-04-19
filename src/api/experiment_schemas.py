# src/api/experiment_schemas.py
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExperimentRunRequest(BaseModel):
    dataset: str = Field(default="src/experiments/datasets/basic.json")
    configs_dir: str = Field(default="src/experiments/configs")
    selected_config_names: Optional[List[str]] = None
    selected_models: Optional[List[str]] = None
    use_all_models: bool = False
    default_model: Optional[str] = None
    timeout_seconds: int = 120
    db_path: str = "src/experiments/results/results.sqlite3"
    output_dir: str = "src/experiments/results"


class ExperimentRunResponse(BaseModel):
    job_id: str
    status: str


class ExperimentJobStatus(BaseModel):
    job_id: str
    status: str
    experiment_run_id: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class ExperimentCatalogResponse(BaseModel):
    datasets: List[str]
    configs: List[str]
    models: List[str]


class ExperimentRunInfo(BaseModel):
    run_id: str
    files: List[str]


class ExperimentRunDetail(BaseModel):
    run_id: str
    manifest: Dict[str, Any]
    configs: Dict[str, List[str]]