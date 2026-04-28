from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ConfigCreate(BaseModel):
    config_id: Optional[str] = None
    name: str
    model: str = "gemma3:4b"
    system_prompt: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class ConfigUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class OffspringCreateRequest(BaseModel):
    count: int = 3
    name_prefix: Optional[str] = None
    mutation_strategy: str = "small_variation"
