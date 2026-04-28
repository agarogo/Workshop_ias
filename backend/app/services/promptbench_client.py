import json
from typing import Any, AsyncIterator

import httpx

from app.core.settings import settings


class PromptBenchClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.promptbench_base_url).rstrip("/")

    async def stream_batch(
        self,
        batch_items: list[dict[str, Any]],
        batch_stream_url: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        url = batch_stream_url or f"{self.base_url}/gateway/batch/stream"
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            async with client.stream("POST", url, json=batch_items, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        yield {"raw": data}
