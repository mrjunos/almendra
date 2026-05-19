"""Repository path resolution.

Central place that locates the repo root and the data directories, so no module
hard-codes a relative path. Override the root with the ALMENDRA_ROOT env var.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Locate the almendra repository root (the dir containing pyproject.toml)."""
    env = os.environ.get("ALMENDRA_ROOT")
    if env:
        return Path(env)
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    raise FileNotFoundError(
        "Could not locate the almendra repository root. Set the ALMENDRA_ROOT environment variable."
    )


def data_dir() -> Path:
    return repo_root() / "data"


def raw_dir() -> Path:
    """Downloaded datasets (DVC-managed, git-ignored)."""
    return data_dir() / "raw"


def processed_dir() -> Path:
    """Ingested single-bean crops + the manifest (DVC-managed, git-ignored)."""
    return data_dir() / "processed"


def sources_dir() -> Path:
    """Per-dataset adapter YAMLs."""
    return data_dir() / "sources"


def configs_dir() -> Path:
    return repo_root() / "configs"
