#!/usr/bin/env python3
"""Builds the installable CaliShelf Calibre plugin ZIP.

Copies the top-level `calishelf/` core engine into `calibre_plugin/calishelf/`
(so it is importable as calibre_plugins.calishelf.calishelf.*), then zips the
contents of `calibre_plugin/` (files at the zip root, not nested in a folder)
into `dist/CaliShelf.zip`.

Note: `calibre-customize -b calibre_plugin` (used for local dev-mode
installs) builds its own zip directly from the calibre_plugin/ folder,
bypassing dist/CaliShelf.zip entirely -- staging steps below must therefore
write into calibre_plugin/ itself, not just into the dist zip.

Usage:
    python scripts/build_plugin_zip.py
"""

import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "calishelf"
PLUGIN_DIR = REPO_ROOT / "calibre_plugin"
VENDORED_CORE_DIR = PLUGIN_DIR / "calishelf"
DIST_DIR = REPO_ROOT / "dist"
OUTPUT_ZIP = DIST_DIR / "CaliShelf.zip"

EXCLUDE_DIR_NAMES = {"__pycache__"}


def stage_core_module():
    if VENDORED_CORE_DIR.exists():
        shutil.rmtree(VENDORED_CORE_DIR)
    shutil.copytree(
        CORE_DIR,
        VENDORED_CORE_DIR,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def build_zip():
    DIST_DIR.mkdir(exist_ok=True)
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()

    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(PLUGIN_DIR.rglob("*")):
            if path.is_dir():
                continue
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            arcname = path.relative_to(PLUGIN_DIR)
            zf.write(path, arcname)

    print(f"Built {OUTPUT_ZIP.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    stage_core_module()
    build_zip()
