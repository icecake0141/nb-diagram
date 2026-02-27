from __future__ import annotations

import sys
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


def same_text(a: Path, b: Path) -> bool:
    return a.read_text(encoding="utf-8") == b.read_text(encoding="utf-8")


def main() -> int:
    missing: list[str] = []
    mismatched: list[str] = []

    for src_name, out_name in FILES.items():
        src = SRC_DIR / src_name
        dst_static = STATIC_DIR / out_name
        dst_dist = DIST_DIR / out_name

        for p in (src, dst_static, dst_dist):
            if not p.exists():
                missing.append(str(p.relative_to(ROOT)))

        if missing:
            continue

        if not same_text(src, dst_static):
            mismatched.append(f"{src.relative_to(ROOT)} != {dst_static.relative_to(ROOT)}")
        if not same_text(src, dst_dist):
            mismatched.append(f"{src.relative_to(ROOT)} != {dst_dist.relative_to(ROOT)}")

    if missing or mismatched:
        if missing:
            print("Missing frontend sync files:")
            for item in missing:
                print(f"  - {item}")
        if mismatched:
            print("Out-of-sync frontend files:")
            for item in mismatched:
                print(f"  - {item}")
        print("Run: python3 scripts/sync_frontend.py")
        return 1

    print("frontend sync check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
