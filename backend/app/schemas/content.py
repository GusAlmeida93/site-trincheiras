from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LessonWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    position: int = 0
    is_published: bool = True


class LessonRead(LessonWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class FlipCardData(BaseModel):
    intel_key: str
    tag: str
    photo_class: str
    foot: str
    back_title: str
    back_text: str


class ParticipantData(BaseModel):
    participant_key: str
    title: str
    leader: str
    role: str
    text: str
    objectives: list[str]
    quote: str


class ClauseData(BaseModel):
    article_key: str
    icon_svg: str
    number: str
    title: str
    quote: str
    impact: str


CONTENT_DATA_MODELS: dict[str, type[BaseModel]] = {
    "flip_card": FlipCardData,
    "participant": ParticipantData,
    "clause": ClauseData,
}

ContentBlockKind = Literal["flip_card", "participant", "clause"]


class ContentBlockWrite(BaseModel):
    kind: ContentBlockKind
    slug: str = Field(min_length=1, max_length=100)
    position: int = 0
    data: dict[str, Any]

    @model_validator(mode="after")
    def _validate_data_shape(self) -> "ContentBlockWrite":
        CONTENT_DATA_MODELS[self.kind].model_validate(self.data)
        return self


class ContentBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ContentBlockKind
    slug: str
    position: int
    data: dict[str, Any]
