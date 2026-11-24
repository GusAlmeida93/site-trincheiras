from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AnswerCreate(BaseModel):
    # Nullable: anonymous play never blocks the games.
    player_id: int | None = None
    question_id: int
    # Option slug (quiz) or document slug (match).
    selected_value: str = Field(min_length=1)
    is_correct: bool
    score_delta: int = 0


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int | None
    question_id: int
    selected_value: str
    is_correct: bool
    score_delta: int
    created_at: datetime
