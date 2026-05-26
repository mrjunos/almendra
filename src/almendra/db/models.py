"""Catalog schema — SQLModel tables (SQLite now, Postgres-portable).

Design notes
------------
- **Multi-label by construction**: defects hang off ``BeanDefect`` (a bean ↔
  defect junction), so a bean can carry any number of defects. ``is_primary``
  marks the SCA most-severe one (used for grading and any single-label export).
- **Provenance lives on ``Lot``**: a lot is a batch of beans that share origin.
  Public datasets get one synthetic lot per source (most fields null); private
  beans get a real lot with farm/variety/altitude/process/dates/humidity.
- **Label trust is explicit**: every ``BeanDefect`` records ``label_source`` and
  a ``trust`` score, so weak dataset labels and human-verified labels coexist.
- Enums are plain strings (portable, no DB-specific enum types); the allowed
  values live in the module-level constants below.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlmodel import Field, SQLModel

# --- enum-like string domains ---------------------------------------------------
PROVENANCE_PUBLIC = "public_dataset"
PROVENANCE_PRIVATE = "proprietary"

STATUS_USABLE = "usable"
STATUS_REFERENCE_ONLY = "reference_only"
STATUS_LICENSE_UNVERIFIED = "license_unverified"

LABEL_DATASET = "dataset"
LABEL_HUMAN = "human_verified"
LABEL_MODEL_WEAK = "model_weak"

SPECTRUM_RGB = "rgb"

# Default trust per label source — dataset labels are weak, human labels strong.
DEFAULT_TRUST = {LABEL_DATASET: 0.5, LABEL_HUMAN: 1.0, LABEL_MODEL_WEAK: 0.25}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Source(SQLModel, table=True):
    """A dataset or origin the beans came from (mirrors ``data/sources/*.yaml``)."""

    __tablename__ = "source"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    title: str = ""
    url: str = ""
    provider: str = ""
    license: str = ""
    commercial_use: bool | None = None
    status: str = STATUS_USABLE
    provenance_type: str = PROVENANCE_PUBLIC
    species_default: str | None = None
    roast: str | None = None
    capture: str | None = None
    notes: str = ""


class Lot(SQLModel, table=True):
    """A batch of beans sharing provenance. Most fields are null for public lots."""

    __tablename__ = "lot"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(foreign_key="source.id", index=True)
    provenance_type: str = PROVENANCE_PUBLIC
    name: str = ""
    farm: str | None = None
    producer: str | None = None
    region: str | None = None
    country: str | None = None
    altitude_masl: int | None = None
    variety: str | None = None
    species: str | None = None
    process: str | None = None  # washed | natural | honey
    harvest_date: date | None = None
    wash_date: date | None = None
    hulling_date: date | None = None
    humidity_pct: float | None = None
    screen_size: str | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class DefectClass(SQLModel, table=True):
    """Canonical defect taxonomy (seeded from ``data/taxonomy.yaml``)."""

    __tablename__ = "defect_class"

    index: int = Field(primary_key=True)  # fixed stability contract — never renumber
    name: str = Field(index=True, unique=True)
    category: int = 0  # 0 none, 1 SCA primary, 2 SCA secondary
    accept: bool = True
    full_defect_equivalent: float = 0.0
    description: str = ""


class MorphologyClass(SQLModel, table=True):
    """Bean shape/genetics axis (separate from defects; seeded from taxonomy)."""

    __tablename__ = "morphology_class"

    index: int = Field(primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str = ""


class Bean(SQLModel, table=True):
    """One singulated green bean."""

    __tablename__ = "bean"

    id: int | None = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="lot.id", index=True)
    ext_id: str = Field(index=True)  # source/human id, e.g. roboflow_robusta_defects_000000
    morphology_index: int = Field(default=0, foreign_key="morphology_class.index")
    screen_size: str | None = None
    is_floater: bool = False
    split: str = "train"  # train | val | test
    is_good: bool = True  # quality gate — export filters on this
    notes: str = ""
    created_at: datetime = Field(default_factory=_utcnow)


class BeanView(SQLModel, table=True):
    """An image view of a bean (multi-view + multi-spectral ready)."""

    __tablename__ = "bean_view"

    id: int | None = Field(default=None, primary_key=True)
    bean_id: int = Field(foreign_key="bean.id", index=True)
    path: str  # relative to the processed root
    view_index: int = 0
    spectrum: str = SPECTRUM_RGB  # rgb | nir | uv
    source_image: str = ""
    capture_session_id: str | None = None


class BeanDefect(SQLModel, table=True):
    """A defect observed on a bean — the multi-label junction (the heart)."""

    __tablename__ = "bean_defect"

    bean_id: int = Field(foreign_key="bean.id", primary_key=True)
    defect_index: int = Field(foreign_key="defect_class.index", primary_key=True)
    is_primary: bool = False  # the SCA most-severe defect on this bean
    label_source: str = LABEL_DATASET  # dataset | human_verified | model_weak
    trust: float = 0.5  # 0..1
    labeler: str | None = None
    labeled_at: datetime | None = None
