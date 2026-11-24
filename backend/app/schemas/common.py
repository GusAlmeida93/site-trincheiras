from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthStatus(BaseModel):
    status: str = "ok"


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
