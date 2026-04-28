from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.api.schemas.configs import ConfigCreate, ConfigUpdate, OffspringCreateRequest
from app.services.config_service import create_config, create_offspring, update_config
from app.storage.config_store import get_config, get_family, list_configs

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("")
async def get_configs():
    return JSONResponse(content=list_configs())


@router.get("/{config_id}")
async def get_config_endpoint(config_id: str):
    payload = get_config(config_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    return JSONResponse(content=payload)


@router.post("")
async def create_config_endpoint(body: ConfigCreate):
    payload = create_config(body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.put("/{config_id}")
async def update_config_endpoint(config_id: str, body: ConfigUpdate):
    payload = update_config(config_id, body.model_dump(exclude_none=True))
    return JSONResponse(content=payload)


@router.get("/{config_id}/lineage")
async def get_config_lineage(config_id: str):
    payload = get_config(config_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    family_id = payload.get("family_id")
    family = get_family(family_id)
    if not family:
        raise HTTPException(status_code=404, detail=f"Family not found: {family_id}")
    return JSONResponse(content=family)


@router.post("/{config_id}/offspring")
async def create_offspring_endpoint(config_id: str, body: OffspringCreateRequest):
    payload = create_offspring(config_id, count=body.count, name_prefix=body.name_prefix)
    return JSONResponse(content=payload)
