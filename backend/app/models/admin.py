from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at_col, intpk


class AdminUser(Base):
    """A teacher account. Created only by the invite-admin ops task."""

    __tablename__ = "admin_users"

    id: Mapped[intpk]
    # Stored lower-case; see services.accounts.normalize_email.
    email: Mapped[str] = mapped_column(sa.String(254), unique=True)
    # NULL until the invite link has been used.
    password_hash: Mapped[str | None] = mapped_column(sa.Text)
    is_active: Mapped[bool] = mapped_column(server_default=sa.true())
    # Keyed digest of the one outstanding invite / password-reset token.
    setup_token_hash: Mapped[str | None] = mapped_column(sa.String(64), unique=True)
    setup_token_expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    created_at: Mapped[created_at_col]
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    sessions: Mapped[list["AdminSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class AdminSession(Base):
    """One signed-in browser. Deleting the row signs it out."""

    __tablename__ = "admin_sessions"

    id: Mapped[intpk]
    admin_user_id: Mapped[int] = mapped_column(
        sa.ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    # Keyed digest of the cookie value; the value itself is never stored.
    token_hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    created_at: Mapped[created_at_col]
    expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True)

    user: Mapped[AdminUser] = relationship(back_populates="sessions")


class LoginThrottle(Base):
    """Failed sign-in attempts per e-mail inside the current window."""

    __tablename__ = "login_throttles"

    # The normalized e-mail that was tried, whether or not an account exists.
    key: Mapped[str] = mapped_column(sa.String(254), primary_key=True)
    failures: Mapped[int]
    window_started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
