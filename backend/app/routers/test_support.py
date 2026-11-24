"""Test-only endpoints. Mounted exclusively when APP_ENV=test (see main.py)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(prefix="/api/v1/test", tags=["test-support"])


@router.post("/reset", include_in_schema=False)
def reset_volatile_data(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    # Content (lessons/questions/...) is seeded and stable; only the rows the
    # e2e suite creates get wiped between specs.
    db.execute(text("TRUNCATE players, answers RESTART IDENTITY CASCADE"))
    db.commit()
    return {"status": "reset"}
