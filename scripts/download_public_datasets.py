#!/usr/bin/env python3
"""Download the public datasets declared in ``data/sources/*.yaml``.

Each source YAML declares a ``download`` block with a ``method``. This script
dispatches on that method, is defensive about missing optional dependencies and
credentials, and writes payloads under ``data/raw/<source>/`` (DVC-managed and
git-ignored — see .gitignore).

Datasets are never redistributed by this project: this script pulls each one
from its original host under its own licence.

Usage::

    python scripts/download_public_datasets.py            # all eligible sources
    python scripts/download_public_datasets.py --only usk_coffee
    python scripts/download_public_datasets.py --list     # list sources, no download
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO_ROOT / "data" / "sources"
RAW_DIR = REPO_ROOT / "data" / "raw"

# Sources with these statuses are skipped unless explicitly named with --only.
SKIP_STATUSES = {"license_unverified"}


def load_sources() -> list[dict]:
    """Parse every ``data/sources/*.yaml`` adapter into a dict."""
    sources = []
    for path in sorted(SOURCES_DIR.glob("*.yaml")):
        with path.open() as fh:
            cfg = yaml.safe_load(fh)
        cfg["_path"] = path
        sources.append(cfg)
    return sources


def _hint(message: str) -> None:
    print(f"  ! {message}")


def download_huggingface(cfg: dict, dest: Path) -> bool:
    """Download a Hugging Face dataset repo via huggingface_hub."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        _hint("huggingface_hub not installed — run: uv sync --extra data")
        return False
    dl = cfg["download"]
    snapshot_download(
        repo_id=dl["repo_id"],
        repo_type=dl.get("repo_type", "dataset"),
        local_dir=str(dest),
    )
    return True


def download_kagglehub(cfg: dict, dest: Path) -> bool:
    """Download a Kaggle dataset via kagglehub."""
    try:
        import kagglehub
    except ImportError:
        _hint("kagglehub not installed — run: uv sync --extra data")
        return False
    path = kagglehub.dataset_download(cfg["download"]["dataset"])
    _hint(f"kagglehub cached the dataset at: {path}")
    _hint(f"symlink or copy it into {dest} before ingestion")
    return True


def download_roboflow(cfg: dict, dest: Path) -> bool:
    """Download a Roboflow Universe dataset via the roboflow SDK."""
    import os

    try:
        from roboflow import Roboflow
    except ImportError:
        _hint("roboflow not installed — run: uv pip install roboflow")
        return False
    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        _hint("set ROBOFLOW_API_KEY (free key at https://roboflow.com)")
        return False
    dl = cfg["download"]
    missing = [k for k in ("workspace", "project", "version") if k not in dl]
    if missing:
        _hint(f"add {missing} to the `download:` block of {cfg['_path'].name}")
        _hint(f"(read them from the dataset page: {cfg['url']})")
        return False
    rf = Roboflow(api_key=api_key)
    project = rf.workspace(dl["workspace"]).project(dl["project"])
    project.version(dl["version"]).download(dl.get("format", "coco"), location=str(dest))
    return True


def download_url(cfg: dict, dest: Path) -> bool:
    """Download a direct file URL, or print manual instructions for a portal."""
    from urllib.request import urlretrieve

    direct = cfg["download"].get("direct_url")
    if not direct:
        _hint("no direct file URL — download manually from the portal:")
        _hint(f"  {cfg['url']}")
        _hint(f"then extract into {dest}")
        return False
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / Path(direct).name
    print(f"  downloading {direct}")
    urlretrieve(direct, target)  # noqa: S310 - trusted, declared dataset host
    return True


DISPATCH = {
    "huggingface": download_huggingface,
    "kagglehub": download_kagglehub,
    "roboflow": download_roboflow,
    "url": download_url,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="download a single source by name")
    parser.add_argument("--list", action="store_true", help="list sources and exit")
    args = parser.parse_args()

    sources = load_sources()
    if not sources:
        print(f"No source adapters found in {SOURCES_DIR}")
        return 1

    if args.list:
        for cfg in sources:
            print(
                f"  {cfg['name']:<26} {cfg.get('status', '?'):<18} "
                f"{cfg.get('license', '?')}  ({cfg['download']['method']})"
            )
        return 0

    failures = 0
    for cfg in sources:
        name = cfg["name"]
        if args.only and name != args.only:
            continue
        status = cfg.get("status", "")
        if status in SKIP_STATUSES and name != args.only:
            print(f"- {name}: skipped (status={status})")
            continue

        method = cfg["download"]["method"]
        handler = DISPATCH.get(method)
        print(f"> {name} (method={method})")
        if handler is None:
            _hint(f"unknown download method: {method}")
            failures += 1
            continue

        dest = RAW_DIR / name
        try:
            ok = handler(cfg, dest)
        except Exception as exc:  # noqa: BLE001 - report and continue
            _hint(f"failed: {exc}")
            ok = False
        if ok:
            print(f"  done -> {dest}")
        else:
            failures += 1

    if failures:
        print(f"\n{failures} source(s) need attention (see hints above).")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
