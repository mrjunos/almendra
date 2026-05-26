"""Centralized bean catalog.

A local SQLite database (Postgres-portable via SQLModel) that is the source of
truth for every bean: its image views, its (possibly multiple) defects with
label provenance/trust, and the provenance of the lot it came from. Image files
stay on disk under ``data/processed/``; the catalog stores relative paths.

The training pipeline stays decoupled: ``almendra db export-manifest`` writes a
manifest the existing data loaders consume.
"""

from __future__ import annotations

from almendra.db.catalog import default_db_path, get_engine, get_session, init_db
from almendra.db.models import (
    Bean,
    BeanDefect,
    BeanView,
    DefectClass,
    Lot,
    MorphologyClass,
    Source,
)

__all__ = [
    "Bean",
    "BeanDefect",
    "BeanView",
    "DefectClass",
    "Lot",
    "MorphologyClass",
    "Source",
    "default_db_path",
    "get_engine",
    "get_session",
    "init_db",
]
