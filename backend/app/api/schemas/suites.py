from typing import List, Optional

from pydantic import BaseModel, Field


class SuiteCreate(BaseModel):
    suite_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    test_ids: List[str] = Field(default_factory=list)


class SuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    test_ids: Optional[List[str]] = None
