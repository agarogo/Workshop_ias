from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TestCreate(BaseModel):
    test_id: Optional[str] = None
    name: str
    system_prompt: Optional[str] = None
    user_prompt: str
    checks: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class TestUpdate(BaseModel):
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    checks: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
