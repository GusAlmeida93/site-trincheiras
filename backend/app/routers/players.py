from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.players import PlayerCreate, PlayerRead
from app.services import players as players_service

router = APIRouter(prefix="/api/v1/players", tags=["players"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_player(
    payload: PlayerCreate, db: Annotated[Session, Depends(get_db)]
) -> PlayerRead:
    player = players_service.create_player(db, payload)
    db.commit()
    return PlayerRead.model_validate(player)
