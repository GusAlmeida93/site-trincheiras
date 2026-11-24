"""Invite a teacher from a shell that can reach the database.

    python -m app.invite_admin prof@example.com [--hours 48]

The same thing the `invite-admin` ops task does (production uses that one:
its database has no public address). Prints a one-time link path where the
teacher sets their own password; run it again to reset a password.
"""

import argparse

from app.config import get_settings
from app.db import get_session_factory
from app.services import accounts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or re-invite a teacher account.")
    parser.add_argument("email")
    parser.add_argument(
        "--hours",
        type=int,
        default=accounts.INVITE_DEFAULT_HOURS,
        choices=range(1, accounts.INVITE_MAX_HOURS + 1),
        metavar=f"1-{accounts.INVITE_MAX_HOURS}",
        help="how long the link stays valid (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    secret = get_settings().session_secret
    if not secret:
        parser.exit(1, "Sign-in is disabled: set SESSION_SECRET first.\n")
    try:
        accounts.normalize_email(args.email)
    except ValueError:
        parser.exit(2, f"Not an e-mail address: {args.email}\n")

    session = get_session_factory()()
    try:
        invite = accounts.invite_admin(session, secret, args.email, args.hours)
        session.commit()
    finally:
        session.close()

    print(f"{'Created' if invite.created else 'Re-invited'} {invite.email}.")
    print(f"Setup link (works once, until {invite.expires_at:%Y-%m-%d %H:%M} UTC):")
    print(f"  <site address>{invite.setup_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
