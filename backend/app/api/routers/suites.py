from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas.suites import SuiteCreate, SuiteUpdate
from app.services.suite_service import create_suite, remove_suite, update_suite
from app.storage.suite_store import get_suite, list_suites

router = APIRouter(prefix="/suites", tags=["suites"])


@router.get("")
async def get_suites():
    return JSONResponse(content=list_suites())


@router.get("/{suite_id}")
async def get_suite_endpoint(suite_id: str):
    payload = get_suite(suite_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Suite not found: {suite_id}")
    return JSONResponse(content=payload)


@router.post("")
async def create_suite_endpoint(body: SuiteCreate):
    payload = create_suite(body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.put("/{suite_id}")
async def update_suite_endpoint(suite_id: str, body: SuiteUpdate):
    payload = update_suite(suite_id, body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.delete("/{suite_id}")
async def delete_suite_endpoint(suite_id: str):
    remove_suite(suite_id)
    return {"deleted": True, "suite_id": suite_id}
