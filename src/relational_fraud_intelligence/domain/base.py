"""Base model class for all domain objects."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
