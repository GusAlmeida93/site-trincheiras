"""Teacher accounts: invites, passwords, sessions and sign-in throttling.

Owns admin_users, admin_sessions and login_throttles.

Everything here is a database row on purpose. Lambda keeps no memory between
requests and runs many sandboxes at once, so a session, an invite or a failure
counter held in the process would be invisible to the next request.

Tokens (the session cookie value, the invite link) are random and are never
stored: the tables keep HMAC-SHA256(SESSION_SECRET, token). A copy of the
database is therefore not enough to forge a session or to use an invite.
"""

import hashlib
import hmac
import math
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import AdminSession, AdminUser, LoginThrottle

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW = timedelta(minutes=15)
INVITE_DEFAULT_HOURS = 48
INVITE_MAX_HOURS = 168
PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
EMAIL_MAX_LENGTH = 254
SETUP_PAGE_PATH = "/admin/definir-senha"

# argon2id with the library defaults (RFC 9106 low-memory profile: 64 MiB,
# 3 passes, 4 lanes). The parameters travel inside each hash.
_hasher = PasswordHasher()


class SignInDisabledError(RuntimeError):
    """SESSION_SECRET is not configured."""


def now() -> datetime:
    return datetime.now(UTC)


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    local, _, domain = email.partition("@")
    if (
        not local
        or "." not in domain.strip(".")
        or "@" in domain
        or any(ch.isspace() for ch in email)
        or len(email) > EMAIL_MAX_LENGTH
    ):
        raise ValueError("not a valid e-mail address")
    return email


def token_digest(secret: str, purpose: str, token: str) -> str:
    if not secret:
        raise SignInDisabledError("SESSION_SECRET is not configured.")
    return hmac.new(
        secret.encode(), f"{purpose}:{token}".encode(), hashlib.sha256
    ).hexdigest()


# --- invites and passwords ---------------------------------------------------


@dataclass(frozen=True)
class Invite:
    email: str
    created: bool
    setup_path: str
    expires_at: datetime


def invite_admin(
    session: Session,
    secret: str,
    email: str,
    expires_in_hours: int = INVITE_DEFAULT_HOURS,
) -> Invite:
    """Create the account if needed and issue a fresh one-time setup link.

    Re-inviting replaces any earlier link. An existing password keeps working
    until the new link is used, so the same call is the password reset.
    """
    email = normalize_email(email)
    token = secrets.token_urlsafe(32)
    digest = token_digest(secret, "setup", token)
    expires_at = now() + timedelta(hours=expires_in_hours)

    user = session.scalar(select(AdminUser).where(AdminUser.email == email))
    created = user is None
    if user is None:
        user = AdminUser(email=email)
        session.add(user)
    user.is_active = True
    user.setup_token_hash = digest
    user.setup_token_expires_at = expires_at
    session.flush()
    # The token rides in the fragment: browsers never send that part to a
    # server, so it stays out of access logs and Referer headers.
    return Invite(
        email=email,
        created=created,
        setup_path=f"{SETUP_PAGE_PATH}#{token}",
        expires_at=expires_at,
    )


def set_password(
    session: Session, secret: str, token: str, password: str
) -> AdminUser | None:
    """Redeem a setup link. None when the link is unknown, used or expired."""
    user = session.scalar(
        select(AdminUser)
        .where(
            AdminUser.setup_token_hash == token_digest(secret, "setup", token),
            AdminUser.setup_token_expires_at > now(),
            AdminUser.is_active,
        )
        .with_for_update()
    )
    if user is None:
        return None
    user.password_hash = _hasher.hash(password)
    user.password_changed_at = now()
    user.setup_token_hash = None
    user.setup_token_expires_at = None
    # A new password signs out every browser and lifts any lock-out.
    session.execute(delete(AdminSession).where(AdminSession.admin_user_id == user.id))
    session.execute(delete(LoginThrottle).where(LoginThrottle.key == user.email))
    session.flush()
    return user


@lru_cache(maxsize=1)
def _decoy_hash() -> str:
    return _hasher.hash(secrets.token_urlsafe(16))


def verify_credentials(session: Session, email: str, password: str) -> AdminUser | None:
    user = session.scalar(
        select(AdminUser).where(
            AdminUser.email == email,
            AdminUser.is_active,
            AdminUser.password_hash.is_not(None),
        )
    )
    # An unknown e-mail costs the same argon2 work as a wrong password, so the
    # response time does not reveal which accounts exist.
    stored = user.password_hash if user is not None else _decoy_hash()
    assert stored is not None
    try:
        _hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return None
    if user is None:
        return None
    if _hasher.check_needs_rehash(stored):
        user.password_hash = _hasher.hash(password)
    return user


def deactivate_admin(session: Session, email: str) -> bool:
    """Shut an account: no sign-in, no sessions, no pending link, no password."""
    user = session.scalar(
        select(AdminUser).where(AdminUser.email == normalize_email(email))
    )
    if user is None:
        return False
    user.is_active = False
    user.password_hash = None
    user.setup_token_hash = None
    user.setup_token_expires_at = None
    session.execute(delete(AdminSession).where(AdminSession.admin_user_id == user.id))
    session.flush()
    return True


def list_admins(session: Session) -> list[dict[str, object]]:
    current = now()
    rows = session.execute(
        select(
            AdminUser.email,
            AdminUser.is_active,
            AdminUser.password_hash.is_not(None).label("has_password"),
            (AdminUser.setup_token_expires_at > current).label("invite_pending"),
            AdminUser.last_login_at,
        ).order_by(AdminUser.email)
    )
    return [
        {
            "email": row.email,
            "is_active": row.is_active,
            "has_password": row.has_password,
            "invite_pending": bool(row.invite_pending),
            "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
        }
        for row in rows
    ]


# --- sessions ----------------------------------------------------------------


def create_session(
    session: Session, secret: str, user: AdminUser, hours: int
) -> tuple[str, datetime]:
    """Returns the cookie value and when it stops working."""
    current = now()
    # Housekeeping rides on sign-in: nothing else would ever remove old rows.
    session.execute(delete(AdminSession).where(AdminSession.expires_at <= current))
    token = secrets.token_urlsafe(32)
    expires_at = current + timedelta(hours=hours)
    session.add(
        AdminSession(
            admin_user_id=user.id,
            token_hash=token_digest(secret, "session", token),
            expires_at=expires_at,
        )
    )
    user.last_login_at = current
    session.flush()
    return token, expires_at


def get_session_user(session: Session, secret: str, token: str) -> AdminUser | None:
    return session.scalar(
        select(AdminUser)
        .join(AdminSession, AdminSession.admin_user_id == AdminUser.id)
        .where(
            AdminSession.token_hash == token_digest(secret, "session", token),
            AdminSession.expires_at > now(),
            AdminUser.is_active,
        )
    )


def end_session(session: Session, secret: str, token: str) -> None:
    session.execute(
        delete(AdminSession).where(
            AdminSession.token_hash == token_digest(secret, "session", token)
        )
    )


# --- sign-in throttling ------------------------------------------------------


def throttle_retry_after(session: Session, key: str) -> int:
    """Seconds until `key` may try again; 0 when it may try now."""
    row = session.execute(
        select(LoginThrottle.failures, LoginThrottle.window_started_at).where(
            LoginThrottle.key == key
        )
    ).one_or_none()
    if row is None or row.failures < LOGIN_MAX_FAILURES:
        return 0
    remaining = (row.window_started_at + LOGIN_WINDOW - now()).total_seconds()
    return max(0, math.ceil(remaining))


def record_failure(session: Session, key: str) -> None:
    current = now()
    # Dropping finished windows first keeps the table small and means the
    # upsert below only ever counts inside a live window.
    session.execute(
        delete(LoginThrottle).where(
            LoginThrottle.window_started_at <= current - LOGIN_WINDOW
        )
    )
    session.execute(
        pg_insert(LoginThrottle)
        .values(key=key, failures=1, window_started_at=current)
        .on_conflict_do_update(
            index_elements=[LoginThrottle.key],
            set_={"failures": LoginThrottle.failures + 1},
        )
    )


def clear_failures(session: Session, key: str) -> None:
    session.execute(delete(LoginThrottle).where(LoginThrottle.key == key))
