from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "frontend" / "src"
STATIC_DIR = ROOT / "static"
DIST_DIR = STATIC_DIR / "dist"

FILES = {
    "app-main.ts": "app-main.js",
    "diagram.ts": "diagram.js",
    "import-workflow.ts": "import-workflow.js",
}


def sync_one(src_name: str, dest_name: str) -> None:
    src = SRC_DIR / src_name
    if not src.exists():
        raise FileNotFoundError(f"Missing source file: {src}")

    text = src.read_text(encoding="utf-8")

    out_static = STATIC_DIR / dest_name
    out_dist = DIST_DIR / dest_name

    out_static.write_text(text, encoding="utf-8")
    out_dist.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for src_name, dest_name in FILES.items():
        sync_one(src_name, dest_name)
    print("synced frontend sources to static/ and static/dist/")
