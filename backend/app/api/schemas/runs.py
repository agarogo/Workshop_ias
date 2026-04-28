from typing import List, Optional

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    suite_id: Optional[str] = None
    selected_test_ids: Optional[List[str]] = None
    config_ids: List[str] = Field(default_factory=list)
    promptbench_batch_stream_url: Optional[str] = None


class SelectBestRequest(BaseModel):
    run_id: str
    test_id: str
    prefer_lower_latency: bool = True
