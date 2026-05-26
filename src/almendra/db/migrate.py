"""Load the existing JSONL manifest into the catalog.

One-way importer for the data we already have: it creates a ``Source`` (if the
seed didn't) + one public ``Lot`` per source, then a ``Bean`` + ``BeanView`` +
``BeanDefect`` per manifest record. Idempotent — keyed on ``(lot, ext_id)`` — so
re-running after adding rows to the manifest only inserts the new beans.
"""

from __future__ import annotations

from pathlib import Path

from sqlmodel import Session, select

from almendra.datasets.manifest import read_manifest
from almendra.db.models import (
    DEFAULT_TRUST,
    LABEL_DATASET,
    PROVENANCE_PUBLIC,
    Bean,
    BeanDefect,
    BeanView,
    Lot,
    Source,
)
from almendra.paths import processed_dir
from almendra.taxonomy import get_taxonomy


def _get_or_create_source(session: Session, name: str) -> Source:
    src = session.exec(select(Source).where(Source.name == name)).first()
    if src is None:
        # Seed normally creates this; fall back to a minimal public source.
        src = Source(name=name, title=name, provenance_type=PROVENANCE_PUBLIC)
        session.add(src)
        session.flush()
    return src


def _get_or_create_public_lot(session: Session, src: Source) -> Lot:
    lot_name = f"{src.name} (public import)"
    lot = session.exec(select(Lot).where(Lot.source_id == src.id, Lot.name == lot_name)).first()
    if lot is None:
        lot = Lot(
            source_id=src.id,
            name=lot_name,
            provenance_type=src.provenance_type,
            species=src.species_default,
        )
        session.add(lot)
        session.flush()
    return lot


def migrate_manifest(session: Session, manifest_path: str | Path | None = None) -> dict[str, int]:
    """Import a manifest into the catalog. Returns counts of new rows."""
    path = Path(manifest_path) if manifest_path else processed_dir() / "manifest.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")

    taxonomy = get_taxonomy()
    morph_index = {name: mc.index for name, mc in taxonomy.morphology_classes.items()}

    counts = {"beans": 0, "views": 0, "defects": 0, "skipped": 0}
    lots: dict[str, Lot] = {}

    for rec in read_manifest(path):
        if rec.source not in lots:
            src = _get_or_create_source(session, rec.source)
            lots[rec.source] = _get_or_create_public_lot(session, src)
        lot = lots[rec.source]

        existing = session.exec(
            select(Bean).where(Bean.lot_id == lot.id, Bean.ext_id == rec.bean_id)
        ).first()
        if existing is not None:
            counts["skipped"] += 1
            continue

        bean = Bean(
            lot_id=lot.id,
            ext_id=rec.bean_id,
            morphology_index=morph_index.get(rec.morphology, 0),
            split=rec.split,
            is_good=True,
        )
        session.add(bean)
        session.flush()  # assign bean.id
        counts["beans"] += 1

        for i, view_path in enumerate(rec.views):
            session.add(
                BeanView(
                    bean_id=bean.id,
                    path=view_path,
                    view_index=i,
                    source_image=rec.source_image,
                )
            )
            counts["views"] += 1

        # Multi-label: store every listed defect; default to the single primary
        # label for legacy records. The primary (SCA most-severe) is the source
        # label here. Sound beans keep an explicit index-0 row (labeled, not unlabeled).
        defect_indices = rec.defects or [rec.defect_index]
        for idx in dict.fromkeys(defect_indices):  # dedupe, preserve order
            session.add(
                BeanDefect(
                    bean_id=bean.id,
                    defect_index=idx,
                    is_primary=(idx == rec.defect_index),
                    label_source=LABEL_DATASET,
                    trust=DEFAULT_TRUST[LABEL_DATASET],
                )
            )
            counts["defects"] += 1

    return counts
