import json
import time
import urllib.request

from fastapi import APIRouter

from src.api.schemas import ModelInfo, ModelsList
from src.config import settings

router = APIRouter()


@router.get("/models", response_model=ModelsList)
async def list_models():
    """Возвращает список реальных Ollama-моделей, если они доступны."""
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            models = payload.get("models", [])

        names = sorted(
            {
                item.get("name") or item.get("model")
                for item in models
                if item.get("name") or item.get("model")
            }
        )

        if names:
            return ModelsList(
                data=[
                    ModelInfo(
                        id=name,
                        created=int(time.time()),
                        owned_by="ollama",
                    )
                    for name in names
                ]
            )
    except Exception:
        pass

    return ModelsList(
        data=[
            ModelInfo(
                id=settings.LLM_MODEL,
                created=int(time.time()),
                owned_by="workshop",
            )
        ]
    )