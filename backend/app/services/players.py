"""Player-identity domain service. Owns the players table."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Answer, Player
from app.schemas.players import DeletionResult, PlayerCreate


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


def _delete_players(session: Session, player_ids: list[int]) -> DeletionResult:
    if not player_ids:
        return DeletionResult(players_deleted=0, answers_deleted=0)
    # answers.player_id is ON DELETE SET NULL (anonymous play is allowed), so
    # removing only the players would leave their answers behind, orphaned.
    answers = session.execute(delete(Answer).where(Answer.player_id.in_(player_ids)))
    players = session.execute(delete(Player).where(Player.id.in_(player_ids)))
    return DeletionResult(
        players_deleted=players.rowcount, answers_deleted=answers.rowcount
    )


def delete_player(session: Session, player_id: int) -> DeletionResult | None:
    """Removes one student and every answer they gave. None if there is no such student."""
    result = _delete_players(
        session,
        list(session.scalars(select(Player.id).where(Player.id == player_id).with_for_update())),
    )
    return result if result.players_deleted else None


def delete_class(session: Session, class_group: str) -> DeletionResult:
    """Removes every student of a class (exact name) and their answers."""
    return _delete_players(
        session,
        list(
            session.scalars(
                select(Player.id).where(Player.class_group == class_group).with_for_update()
            )
        ),
    )
