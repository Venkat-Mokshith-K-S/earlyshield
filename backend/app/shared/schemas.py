"""Shared Pydantic response envelope schemas."""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    success: bool = True
    message: str = "OK"
    data: Optional[DataT] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ORMBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
