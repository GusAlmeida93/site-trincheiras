from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _collapse_whitespace(value: str) -> str:
    return " ".join(value.split())


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    class_group: str = Field(min_length=1, max_length=50)
    recruit_number: str | None = Field(default=None, max_length=50)

    @field_validator("name", "class_group")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = _collapse_whitespace(v)
        if not v:
            raise ValueError("must not be blank")
        return v


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    class_group: str
    recruit_number: str | None
    created_at: datetime
