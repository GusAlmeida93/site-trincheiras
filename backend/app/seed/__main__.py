"""Seed the database with lesson content: python -m app.seed"""

import sys

from app.db import get_session_factory
from app.seed.loader import seed_all


def main() -> int:
    session = get_session_factory()()
    try:
        counts = seed_all(session)
        session.commit()
    except Exception as exc:  # noqa: BLE001 — deploy step must fail loudly
        session.rollback()
        print(f"seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
    for name, count in counts.items():
        print(f"{name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
