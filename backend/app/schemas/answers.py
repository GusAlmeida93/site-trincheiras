from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Primary keys are 32-bit integers in PostgreSQL.
DbId = Annotated[int, Field(ge=1, le=2_147_483_647)]


class AnswerRetry(BaseModel):
    """Marks a request as a re-send of an attempt whose response never arrived.

    If the first send did reach the database, the server answers with that
    recorded answer instead of recording the attempt twice.
    """

    model_config = ConfigDict(extra="forbid")

    # Time since the attempt was first sent.
    elapsed_ms: int = Field(ge=0, le=86_400_000)
    # Last answer id this client received for the player, if any: an older
    # identical answer is then never mistaken for the lost one.
    after_answer_id: DbId | None = None


class AnswerCreate(BaseModel):
    """One attempt at a question. The server decides correctness and score."""

    # Rejects is_correct / score_delta from clients written for the old contract
    # instead of silently ignoring them.
    model_config = ConfigDict(extra="forbid")

    # Null for anonymous play: the attempt is judged but not recorded.
    player_id: DbId | None = None
    question_id: DbId
    # Id of the chosen option (multiple_choice question) or document
    # (match_drawer question), as listed in the lesson bundle.
    choice_id: DbId
    # Anonymous play only: wrong attempts already made at this question in this
    # browser, so the error cap still applies. Ignored when player_id is set
    # (the server counts the recorded answers itself).
    prior_errors: int = Field(default=0, ge=0)
    retry: AnswerRetry | None = None


class AnswerResult(BaseModel):
    # Null when the attempt was judged but not recorded (anonymous play).
    id: int | None
    player_id: int | None
    question_id: int
    choice_id: int
    is_correct: bool
    score_delta: int
    # Text to show after a correct answer; null otherwise.
    feedback: str | None
