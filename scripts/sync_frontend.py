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


def resolve_source(src_name: str, dest_name: str) -> Path:
    src = SRC_DIR / src_name
    if src.exists():
        return src

    # Fallback for environments where source files are missing unexpectedly.
    fallback = STATIC_DIR / dest_name
    if fallback.exists():
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        src.write_text(fallback.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"restored missing source from fallback: {src_name}")
        return src
    raise FileNotFoundError(f"Missing source file: {src}")


def sync_one(src_name: str, dest_name: str) -> None:
    src = resolve_source(src_name, dest_name)

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
