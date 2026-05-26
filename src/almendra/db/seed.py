"""Seed the catalog's reference tables from the canonical YAML.

``defect_class`` / ``morphology_class`` come from ``data/taxonomy.yaml``; the
``source`` rows mirror ``data/sources/*.yaml``. All upserts are idempotent so
re-seeding after a taxonomy or adapter edit just updates the rows.
"""

from __future__ import annotations

import yaml
from sqlmodel import Session, select

from almendra.db.models import DefectClass, MorphologyClass, Source
from almendra.paths import sources_dir
from almendra.taxonomy import Taxonomy, get_taxonomy


def seed_taxonomy(session: Session, taxonomy: Taxonomy | None = None) -> None:
    """Upsert defect + morphology classes from the taxonomy (keyed on index)."""
    tax = taxonomy or get_taxonomy()
    for dc in tax.defect_classes.values():
        row = session.get(DefectClass, dc.index)
        if row is None:
            row = DefectClass(index=dc.index)
        row.name = dc.name
        row.category = dc.category
        row.accept = dc.accept
        row.full_defect_equivalent = dc.full_defect_equivalent
        row.description = dc.description
        session.add(row)
    for mc in tax.morphology_classes.values():
        row = session.get(MorphologyClass, mc.index)
        if row is None:
            row = MorphologyClass(index=mc.index)
        row.name = mc.name
        row.description = mc.description
        session.add(row)


def seed_sources(session: Session) -> int:
    """Upsert one ``Source`` per ``data/sources/*.yaml`` (keyed on name). Returns count."""
    count = 0
    for path in sorted(sources_dir().glob("*.yaml")):
        cfg = yaml.safe_load(path.read_text()) or {}
        name = cfg.get("name") or path.stem
        row = session.exec(select(Source).where(Source.name == name)).first()
        if row is None:
            row = Source(name=name)
        row.title = cfg.get("title", "")
        row.url = cfg.get("url", "")
        row.provider = cfg.get("provider", "")
        row.license = cfg.get("license", "")
        row.commercial_use = cfg.get("commercial_use")
        row.status = cfg.get("status", "usable")
        # Every current adapter is a public dataset; private origins are created
        # explicitly (with provenance_type=proprietary), not seeded from YAML.
        row.provenance_type = cfg.get("provenance_type", "public_dataset")
        row.species_default = cfg.get("species")
        row.roast = cfg.get("roast")
        row.capture = cfg.get("capture")
        row.notes = (cfg.get("notes") or "").strip()
        session.add(row)
        count += 1
    return count


def seed_all(session: Session, taxonomy: Taxonomy | None = None) -> None:
    """Seed taxonomy + sources in one transaction-friendly call."""
    seed_taxonomy(session, taxonomy)
    seed_sources(session)
