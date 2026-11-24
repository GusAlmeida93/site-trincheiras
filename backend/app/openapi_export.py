"""Export the OpenAPI spec without a running server.

Usage:
    python -m app.openapi_export --out openapi.json
    python -m app.openapi_export --check openapi.json   # CI drift gate
"""

import argparse
import json
import sys
from pathlib import Path

from app.main import create_app


def render_spec() -> str:
    app = create_app()
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path, help="write the spec to this path")
    group.add_argument("--check", type=Path, help="fail if the spec differs from this file")
    args = parser.parse_args()

    spec = render_spec()
    if args.out:
        args.out.write_text(spec, encoding="utf-8")
        print(f"wrote {args.out}")
        return 0
    if args.check.read_text(encoding="utf-8") != spec:
        print(
            f"{args.check} is stale — run: python -m app.openapi_export --out {args.check}",
            file=sys.stderr,
        )
        return 1
    print(f"{args.check} is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
