"""Read-side queries for the Data Browser UI.

Kept separate from the UI so they're unit-testable without Streamlit. All
filters are optional; ``None``/empty means "no filter".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlmodel import Session, select

from almendra.db.models import Bean, BeanDefect, BeanView, Lot, Source
from almendra.taxonomy import get_taxonomy

# trust buckets the UI offers — (label, predicate on a trust value)
TRUST_BUCKETS = {
    "all": lambda _t: True,
    "low (<0.3)": lambda t: t < 0.3,
    "mid (0.3–0.7)": lambda t: 0.3 <= t < 0.7,
    "high (≥0.7)": lambda t: t >= 0.7,
}

QUALITY_OPTIONS = ("all", "good only", "not-good only")


@dataclass(frozen=True)
class BeanFilters:
    source: str | None = None
    split: str | None = None
    provenance: str | None = None
    primary_defect: str | None = None  # canonical class name
    quality: str = "all"  # all | good only | not-good only
    trust_bucket: str = "all"


@dataclass
class BeanRow:
    """One row for the gallery/table (primary view + summary)."""

    id: int
    ext_id: str
    source: str
    provenance_type: str
    split: str
    is_good: bool
    primary_defect: str
    n_defects: int
    first_view: str | None
    notes: str


@dataclass
class BeanDetail:
    ext_id: str
    source: str
    is_good: bool
    notes: str
    lot: dict
    morphology: str
    views: list[str] = field(default_factory=list)
    defects: list[dict] = field(default_factory=list)


def distinct_sources(session: Session) -> list[str]:
    return list(session.exec(select(Source.name).order_by(Source.name)).all())


def _primary_defect_index(name: str | None) -> int | None:
    if not name:
        return None
    tax = get_taxonomy()
    return tax.index_of(name) if name in tax.defect_classes else None


def _filtered_bean_ids(session: Session, f: BeanFilters) -> list[int]:
    """Bean ids matching the filters, newest first (id desc)."""
    stmt = (
        select(Bean.id, Bean.is_good)
        .join(Lot, Bean.lot_id == Lot.id)
        .join(Source, Lot.source_id == Source.id)
    )
    if f.source:
        stmt = stmt.where(Source.name == f.source)
    if f.split:
        stmt = stmt.where(Bean.split == f.split)
    if f.provenance:
        stmt = stmt.where(Lot.provenance_type == f.provenance)
    if f.quality == "good only":
        stmt = stmt.where(Bean.is_good == True)  # noqa: E712
    elif f.quality == "not-good only":
        stmt = stmt.where(Bean.is_good == False)  # noqa: E712

    idx = _primary_defect_index(f.primary_defect)
    if idx is not None or f.trust_bucket != "all":
        stmt = stmt.join(
            BeanDefect,
            (BeanDefect.bean_id == Bean.id) & (BeanDefect.is_primary == True),  # noqa: E712
        )
        if idx is not None:
            stmt = stmt.where(BeanDefect.defect_index == idx)

    rows = session.exec(stmt.order_by(Bean.id.desc())).all()

    if f.trust_bucket != "all":
        # trust comes from the joined primary defect; re-query its value per bean
        keep = TRUST_BUCKETS.get(f.trust_bucket, lambda _t: True)
        ids = [bid for (bid, _good) in rows]
        trusts = dict(
            session.exec(
                select(BeanDefect.bean_id, BeanDefect.trust).where(
                    BeanDefect.bean_id.in_(ids),
                    BeanDefect.is_primary == True,  # noqa: E712
                )
            ).all()
        )
        return [bid for (bid, _good) in rows if keep(trusts.get(bid, 1.0))]
    return [bid for (bid, _good) in rows]


def query_page(
    session: Session, f: BeanFilters, *, limit: int = 24, offset: int = 0
) -> tuple[int, list[BeanRow]]:
    """Return (total matching, page of BeanRow)."""
    tax = get_taxonomy()
    defect_name = {dc.index: dc.name for dc in tax.defect_classes.values()}

    ids = _filtered_bean_ids(session, f)
    total = len(ids)
    page_ids = ids[offset : offset + limit]

    rows: list[BeanRow] = []
    for bean_id in page_ids:
        bean, lot, source = session.exec(
            select(Bean, Lot, Source)
            .join(Lot, Bean.lot_id == Lot.id)
            .join(Source, Lot.source_id == Source.id)
            .where(Bean.id == bean_id)
        ).one()
        defects = session.exec(select(BeanDefect).where(BeanDefect.bean_id == bean_id)).all()
        primary = next((d for d in defects if d.is_primary), defects[0] if defects else None)
        first_view = session.exec(
            select(BeanView.path).where(BeanView.bean_id == bean_id).order_by(BeanView.view_index)
        ).first()
        rows.append(
            BeanRow(
                id=bean_id,
                ext_id=bean.ext_id,
                source=source.name,
                provenance_type=lot.provenance_type,
                split=bean.split,
                is_good=bean.is_good,
                primary_defect=defect_name.get(primary.defect_index, "—") if primary else "—",
                n_defects=len(defects),
                first_view=first_view,
                notes=bean.notes,
            )
        )
    return total, rows


def bean_detail(session: Session, bean_id: int) -> BeanDetail:
    tax = get_taxonomy()
    defect_name = {dc.index: dc.name for dc in tax.defect_classes.values()}
    morph_name = {mc.index: mc.name for mc in tax.morphology_classes.values()}

    bean, lot, source = session.exec(
        select(Bean, Lot, Source)
        .join(Lot, Bean.lot_id == Lot.id)
        .join(Source, Lot.source_id == Source.id)
        .where(Bean.id == bean_id)
    ).one()
    views = session.exec(
        select(BeanView.path).where(BeanView.bean_id == bean_id).order_by(BeanView.view_index)
    ).all()
    defects = session.exec(select(BeanDefect).where(BeanDefect.bean_id == bean_id)).all()

    lot_fields = {
        "source": source.name,
        "provenance": lot.provenance_type,
        "species": lot.species,
        "variety": lot.variety,
        "process": lot.process,
        "farm": lot.farm,
        "region": lot.region,
        "country": lot.country,
        "altitude_masl": lot.altitude_masl,
        "harvest_date": str(lot.harvest_date) if lot.harvest_date else None,
        "humidity_pct": lot.humidity_pct,
    }
    return BeanDetail(
        ext_id=bean.ext_id,
        source=source.name,
        is_good=bean.is_good,
        notes=bean.notes,
        lot={k: v for k, v in lot_fields.items() if v not in (None, "")},
        morphology=morph_name.get(bean.morphology_index, "normal"),
        views=list(views),
        defects=sorted(
            (
                {
                    "class": defect_name.get(d.defect_index, str(d.defect_index)),
                    "primary": d.is_primary,
                    "label_source": d.label_source,
                    "trust": d.trust,
                }
                for d in defects
            ),
            key=lambda r: (not r["primary"], r["class"]),
        ),
    )
