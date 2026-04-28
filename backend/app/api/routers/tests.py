from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas.tests import TestCreate, TestUpdate
from app.services.test_service import create_test, remove_test, update_test
from app.storage.test_store import get_test, list_tests

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("")
async def get_tests():
    return JSONResponse(content=list_tests())


@router.get("/{test_id}")
async def get_test_endpoint(test_id: str):
    payload = get_test(test_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Test not found: {test_id}")
    return JSONResponse(content=payload)


@router.post("")
async def create_test_endpoint(body: TestCreate):
    payload = create_test(body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.put("/{test_id}")
async def update_test_endpoint(test_id: str, body: TestUpdate):
    payload = update_test(test_id, body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.delete("/{test_id}")
async def delete_test_endpoint(test_id: str):
    remove_test(test_id)
    return {"deleted": True, "test_id": test_id}
