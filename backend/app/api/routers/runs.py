from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas.runs import RunCreate, SelectBestRequest
from app.services.run_service import create_run, select_best_result
from app.storage.run_store import list_runs, run_bundle

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
async def get_runs():
    return JSONResponse(content=list_runs())


@router.post("")
async def create_run_endpoint(body: RunCreate):
    payload = await create_run(
        suite_id=body.suite_id,
        selected_test_ids=body.selected_test_ids,
        config_ids=body.config_ids,
        batch_stream_url=body.promptbench_batch_stream_url,
    )
    return JSONResponse(content=payload)


@router.get("/{run_id}")
async def get_run_endpoint(run_id: str):
    runs = list_runs()
    manifest = next((item for item in runs if item.get("run_id") == run_id), None)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    dt = datetime.fromisoformat(manifest["created_at"])
    return JSONResponse(content=run_bundle(run_id, dt))


@router.post("/select-best")
async def select_best_endpoint(body: SelectBestRequest):
    payload = select_best_result(body.run_id, body.test_id, body.prefer_lower_latency)
    return JSONResponse(content=payload)
