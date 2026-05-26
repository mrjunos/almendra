"""Export the catalog to a training manifest.

Keeps the training pipeline decoupled from the DB: this writes the same
``manifest.jsonl`` the data loaders already read. Each record carries the full
multi-label ``defects`` list plus the back-compat single ``defect_class`` /
``defect_index`` (= the primary, SCA most-severe defect). Gating lets the export
include only good data and only the provenance you want (public-only by
default; private is opt-in so it is never silently mixed in).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from sqlmodel import Session, select

from almendra.datasets.manifest import BeanRecord, write_manifest
from almendra.db.models import Bean, BeanDefect, BeanView, Lot, Source
from almendra.paths import processed_dir
from almendra.taxonomy import get_taxonomy


def export_manifest(
    session: Session,
    out_path: str | Path | None = None,
    *,
    good_only: bool = True,
    provenance_types: Iterable[str] | None = ("public_dataset",),
    min_trust: float = 0.0,
) -> Path:
    """Write a manifest from the catalog. Returns the path written.

    ``provenance_types=None`` includes every provenance (public + private).
    """
    taxonomy = get_taxonomy()
    defect_name = {dc.index: dc.name for dc in taxonomy.defect_classes.values()}
    morph_name = {mc.index: mc.name for mc in taxonomy.morphology_classes.values()}
    prov = set(provenance_types) if provenance_types is not None else None

    statement = (
        select(Bean, Lot, Source)
        .join(Lot, Bean.lot_id == Lot.id)
        .join(Source, Lot.source_id == Source.id)
    )
    if good_only:
        statement = statement.where(Bean.is_good == True)  # noqa: E712 — SQL boolean

    records: list[BeanRecord] = []
    for bean, lot, source in session.exec(statement).all():
        if prov is not None and lot.provenance_type not in prov:
            continue

        views = session.exec(
            select(BeanView).where(BeanView.bean_id == bean.id).order_by(BeanView.view_index)
        ).all()
        if not views:
            continue  # a bean with no image is useless for training

        defects = session.exec(select(BeanDefect).where(BeanDefect.bean_id == bean.id)).all()
        defects = [d for d in defects if d.trust >= min_trust]
        if not defects:
            continue

        primaries = [d for d in defects if d.is_primary]
        primary_idx = (
            primaries[0].defect_index if primaries else min(d.defect_index for d in defects)
        )
        defect_indices = sorted({d.defect_index for d in defects})

        records.append(
            BeanRecord(
                bean_id=bean.ext_id,
                source=source.name,
                defect_class=defect_name[primary_idx],
                defect_index=primary_idx,
                split=bean.split,
                views=[v.path for v in views],
                morphology=morph_name.get(bean.morphology_index, "normal"),
                source_image=views[0].source_image,
                defects=defect_indices,
            )
        )

    out = Path(out_path) if out_path else processed_dir() / "manifest.jsonl"
    write_manifest(records, out)
    return out
