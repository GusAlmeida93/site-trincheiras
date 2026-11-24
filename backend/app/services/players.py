"""Player-identity domain service. Owns the players table."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Player
from app.schemas.players import PlayerCreate


def create_player(session: Session, data: PlayerCreate) -> Player:
    player = Player(
        name=data.name,
        class_group=data.class_group,
        recruit_number=data.recruit_number,
    )
    session.add(player)
    session.flush()
    return player


def get_player(session: Session, player_id: int) -> Player | None:
    return session.scalar(select(Player).where(Player.id == player_id))
