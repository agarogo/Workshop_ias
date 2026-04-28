from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.services.file_view_service import build_tree, read_relative_json

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/tree")
async def get_tree():
    return JSONResponse(content=build_tree(settings.storage_root))


@router.get("/json")
async def get_json(path: str):
    payload = read_relative_json(path)
    return JSONResponse(content={"path": path, "content": payload})
