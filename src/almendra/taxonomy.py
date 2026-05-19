"""Canonical green coffee bean label schema.

Loads and validates ``data/taxonomy.yaml`` — the single source of truth for the
defect classes the model predicts and the morphology classes it may predict as
a secondary task. The YAML file documents the schema; this module turns it into
validated, typed objects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_ENV_VAR = "ALMENDRA_TAXONOMY"
_CATEGORY_NAMES = {0: "none", 1: "primary", 2: "secondary"}


def _find_repo_root(start: Path) -> Path | None:
    """Walk upward from ``start`` until a directory containing pyproject.toml."""
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return None


def default_taxonomy_path() -> Path:
    """Locate ``data/taxonomy.yaml`` via the ALMENDRA_TAXONOMY env var or repo root."""
    env = os.environ.get(_ENV_VAR)
    if env:
        return Path(env)
    root = _find_repo_root(Path(__file__).resolve())
    if root is None:
        raise FileNotFoundError(
            "Could not locate the repository root. Set the ALMENDRA_TAXONOMY "
            "environment variable to the path of data/taxonomy.yaml."
        )
    return root / "data" / "taxonomy.yaml"


@dataclass(frozen=True)
class DefectClass:
    """One class on the primary (defect) axis."""

    name: str
    index: int
    category: int  # 0 = none, 1 = SCA primary, 2 = SCA secondary
    accept: bool
    full_defect_equivalent: float
    description: str

    @property
    def category_name(self) -> str:
        return _CATEGORY_NAMES[self.category]


@dataclass(frozen=True)
class MorphologyClass:
    """One class on the secondary (morphology) axis."""

    name: str
    index: int
    description: str


class Taxonomy:
    """The validated almendra label schema."""

    def __init__(self, raw: dict):
        self.schema_version: int = raw["schema_version"]
        self.verified: bool = raw.get("verified", False)
        self.reference: str = raw.get("reference", "")
        self.defect_classes: dict[str, DefectClass] = {
            name: DefectClass(name=name, **spec) for name, spec in raw["defect_classes"].items()
        }
        self.morphology_classes: dict[str, MorphologyClass] = {
            name: MorphologyClass(name=name, **spec)
            for name, spec in raw.get("morphology_classes", {}).items()
        }
        self.grading: dict = raw.get("grading", {})
        self.validate()

    # --- construction --------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path | None = None) -> Taxonomy:
        """Load a taxonomy from YAML (defaults to ``data/taxonomy.yaml``)."""
        path = Path(path) if path is not None else default_taxonomy_path()
        with path.open() as fh:
            return cls(yaml.safe_load(fh))

    # --- validation ----------------------------------------------------------
    def validate(self) -> None:
        """Raise ``ValueError`` if the schema is internally inconsistent."""
        if "sound" not in self.defect_classes:
            raise ValueError("taxonomy must define a 'sound' class")

        indices = sorted(c.index for c in self.defect_classes.values())
        if indices != list(range(len(indices))):
            raise ValueError(f"defect class indices must be contiguous from 0, got {indices}")

        for c in self.defect_classes.values():
            if c.category not in _CATEGORY_NAMES:
                raise ValueError(f"{c.name}: category must be 0, 1 or 2")
            if c.full_defect_equivalent < 0:
                raise ValueError(f"{c.name}: full_defect_equivalent must be >= 0")

        m_indices = sorted(c.index for c in self.morphology_classes.values())
        if m_indices and m_indices != list(range(len(m_indices))):
            raise ValueError(f"morphology class indices must be contiguous from 0, got {m_indices}")

    # --- accessors -----------------------------------------------------------
    @property
    def num_defect_classes(self) -> int:
        return len(self.defect_classes)

    def class_names(self) -> list[str]:
        """Defect class names ordered by index — the model's output order."""
        ordered = sorted(self.defect_classes.values(), key=lambda c: c.index)
        return [c.name for c in ordered]

    def morphology_names(self) -> list[str]:
        """Morphology class names ordered by index."""
        ordered = sorted(self.morphology_classes.values(), key=lambda c: c.index)
        return [c.name for c in ordered]

    def index_of(self, name: str) -> int:
        return self.defect_classes[name].index

    def name_of(self, index: int) -> str:
        for c in self.defect_classes.values():
            if c.index == index:
                return c.name
        raise KeyError(f"no defect class with index {index}")

    def is_accept(self, name: str) -> bool:
        """True if a bean of this class passes the sorter."""
        return self.defect_classes[name].accept

    def by_category(self, category: int) -> list[DefectClass]:
        """Defect classes in a given SCA category, ordered by index."""
        members = (c for c in self.defect_classes.values() if c.category == category)
        return sorted(members, key=lambda c: c.index)

    def full_defect_equivalent(self, name: str) -> float:
        """Beans of this class that the SCA counts as one full defect (inverse weight)."""
        return self.defect_classes[name].full_defect_equivalent


@lru_cache(maxsize=1)
def get_taxonomy() -> Taxonomy:
    """Cached load of the default taxonomy (``data/taxonomy.yaml``)."""
    return Taxonomy.load()
