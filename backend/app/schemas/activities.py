from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QuestionOptionWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    position: int = 0
    label: str
    is_correct: bool = False


class QuestionOptionRead(QuestionOptionWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int


class QuestionWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    kind: Literal["multiple_choice", "match_drawer"]
    position: int = 0
    title: str | None = None
    prompt: str
    feedback_correct: str | None = None
    options: list[QuestionOptionWrite] = []

    @model_validator(mode="after")
    def _validate_options(self) -> "QuestionWrite":
        correct = sum(1 for o in self.options if o.is_correct)
        if self.kind == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("multiple_choice questions need at least 2 options")
            if correct != 1:
                raise ValueError("multiple_choice questions need exactly 1 correct option")
        elif correct > 1:
            raise ValueError("at most one option may be correct")
        return self


class QuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: Literal["multiple_choice", "match_drawer"]
    position: int
    title: str | None
    prompt: str
    feedback_correct: str | None
    options: list[QuestionOptionRead]


class MatchDocumentWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    body: str
    position: int = 0
    correct_question_slug: str


class MatchDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    body: str
    position: int
    correct_question_slug: str


class ActivityWrite(BaseModel):
    slug: str = Field(min_length=1, max_length=100)
    kind: Literal["match", "quiz"]
    title: str = Field(min_length=1, max_length=255)
    position: int = 0
    config: dict[str, Any] = {}
    questions: list[QuestionWrite] = []
    documents: list[MatchDocumentWrite] = []

    @model_validator(mode="after")
    def _validate_documents(self) -> "ActivityWrite":
        question_slugs = {q.slug for q in self.questions}
        for doc in self.documents:
            if doc.correct_question_slug not in question_slugs:
                raise ValueError(
                    f"document '{doc.slug}' references unknown question "
                    f"'{doc.correct_question_slug}'"
                )
        return self


class ActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: Literal["match", "quiz"]
    title: str
    position: int
    config: dict[str, Any]
    questions: list[QuestionRead]
    documents: list[MatchDocumentRead]


# --- public (student-facing) views -----------------------------------------
#
# What the browser gets. Nothing here may reveal a correct answer or let one
# be inferred: no verdict flags, no pairings, no feedback texts, and no slugs
# of choices (author-facing names; the seed's doc-N pairs with drawer-N). The
# free-form activity config stays private too. Choices are identified by id.


class PublicQuestionOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    label: str


class PublicQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: Literal["multiple_choice", "match_drawer"]
    position: int
    title: str | None
    prompt: str
    options: list[PublicQuestionOption]


class PublicMatchDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    position: int
    body: str


class PublicActivity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    kind: Literal["match", "quiz"]
    title: str
    position: int
    questions: list[PublicQuestion]
    documents: list[PublicMatchDocument]


class LessonBundle(BaseModel):
    """Everything the browser needs to run a lesson's interactive modules."""

    lesson: "LessonRead"
    map_regions: list["MapRegionRead"]
    activities: list[PublicActivity]


from app.schemas.content import LessonRead  # noqa: E402
from app.schemas.map import MapRegionRead  # noqa: E402

LessonBundle.model_rebuild()
