from datetime import datetime

from pydantic import BaseModel


class PlayerScoreSummary(BaseModel):
    player_id: int
    name: str
    class_group: str
    recruit_number: str | None
    answers_count: int
    correct_count: int
    total_score: int
    last_answer_at: datetime | None


class AnswerReportRow(BaseModel):
    id: int
    player_id: int | None
    player_name: str | None
    class_group: str | None
    activity_slug: str
    question_slug: str
    selected_value: str
    is_correct: bool
    score_delta: int
    created_at: datetime
