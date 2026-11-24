"""Removing students and their answers (teacher clean-up)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.players import DeletionResult
from app.security import require_admin
from app.services import players as players_service

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.delete("/players/{player_id}")
def delete_player(
    player_id: int, db: Annotated[Session, Depends(get_db)]
) -> DeletionResult:
    """Deletes one student together with every answer they recorded."""
    result = players_service.delete_player(db, player_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Player not found.")
    db.commit()
    return result


@router.delete("/players")
def delete_class(
    db: Annotated[Session, Depends(get_db)],
    class_group: Annotated[str, Query(min_length=1, max_length=50)],
) -> DeletionResult:
    """Deletes every student of one class (exact name) and their answers.

    `class_group` is required: there is no way to delete all classes at once.
    """
    result = players_service.delete_class(db, class_group)
    if result.players_deleted == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Class not found.")
    db.commit()
    return result
