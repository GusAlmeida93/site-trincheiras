"""Jinja helper bridging FastAPI templates and Vite assets.

Dev (settings.vite_dev_server set): emit module tags pointing at the Vite dev
server. Prod: resolve hashed filenames from the build manifest.
"""

import json
from pathlib import Path

from markupsafe import Markup

from app.config import get_settings


class ViteManifestError(RuntimeError):
    pass


def _read_manifest(static_dir: Path) -> dict:
    # Vite 5+ writes the manifest inside a .vite subdirectory.
    path = static_dir / "dist" / ".vite" / "manifest.json"
    if not path.exists():
        raise ViteManifestError(
            f"Vite manifest not found at {path}. Run `npm run build` in frontend/, "
            "or set VITE_DEV_SERVER=http://localhost:5173 for development."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def vite_asset(entry: str = "src/main.ts") -> Markup:
    settings = get_settings()
    if settings.vite_dev_server:
        base = settings.vite_dev_server.rstrip("/")
        return Markup(
            f'<script type="module" src="{base}/@vite/client"></script>\n'
            f'  <script type="module" src="{base}/{entry}"></script>'
        )

    manifest = _read_manifest(settings.static_dir)
    if entry not in manifest:
        raise ViteManifestError(f"Entry {entry!r} missing from the Vite manifest.")

    tags: list[str] = []
    seen: set[str] = set()

    def collect_css(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        chunk = manifest[name]
        for imported in chunk.get("imports", []):
            collect_css(imported)
        for css in chunk.get("css", []):
            tags.append(f'<link rel="stylesheet" href="/static/dist/{css}">')

    collect_css(entry)
    entry_chunk = manifest[entry]
    for imported in entry_chunk.get("imports", []):
        tags.append(
            f'<link rel="modulepreload" href="/static/dist/{manifest[imported]["file"]}">'
        )
    tags.append(
        f'<script type="module" src="/static/dist/{entry_chunk["file"]}"></script>'
    )
    return Markup("\n  ".join(tags))
