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
    activity_title: str
    question_slug: str
    question_title: str | None
    selected_value: str
    # Text of the chosen option or document, when the slug still resolves.
    selected_label: str | None
    is_correct: bool
    score_delta: int
    created_at: datetime


class ClassSummary(BaseModel):
    class_group: str
    players_count: int
    answers_count: int
    correct_count: int
    total_score: int
    last_answer_at: datetime | None


class QuestionSummary(BaseModel):
    question_slug: str
    title: str | None
    prompt: str
    answers_count: int
    correct_count: int
    # Distinct enlisted students who tried the question / got it right at
    # least once (a student may answer the same question several times).
    players_count: int
    players_correct_count: int


class ActivitySummary(BaseModel):
    activity_slug: str
    title: str
    kind: str
    players_count: int
    answers_count: int
    correct_count: int
    questions: list[QuestionSummary]
