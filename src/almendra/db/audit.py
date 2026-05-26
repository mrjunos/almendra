"""Catalog health report — what's in the catalog and what needs attention.

Step 1 reports composition (counts by provenance / source / class / split /
label trust) plus integrity flags (license-blocked sources still holding beans,
beans with no image). Near-duplicate detection is added in Step 2 (curation).
"""

from __future__ import annotations

from collections import Counter

from sqlmodel import Session, func, select

from almendra.db.models import (
    STATUS_LICENSE_UNVERIFIED,
    Bean,
    BeanDefect,
    BeanView,
    Lot,
    Source,
)
from almendra.taxonomy import get_taxonomy


def audit_report(session: Session) -> dict:
    """Collect catalog statistics + integrity flags into a dict."""
    taxonomy = get_taxonomy()
    defect_name = {dc.index: dc.name for dc in taxonomy.defect_classes.values()}

    total_beans = session.exec(select(func.count()).select_from(Bean)).one()
    total_views = session.exec(select(func.count()).select_from(BeanView)).one()
    total_defects = session.exec(select(func.count()).select_from(BeanDefect)).one()

    by_provenance: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    by_split: Counter[str] = Counter()
    for bean, lot, source in session.exec(
        select(Bean, Lot, Source)
        .join(Lot, Bean.lot_id == Lot.id)
        .join(Source, Lot.source_id == Source.id)
    ).all():
        by_provenance[lot.provenance_type] += 1
        by_source[source.name] += 1
        by_split[bean.split] += 1

    by_primary: Counter[str] = Counter()
    by_label_source: Counter[str] = Counter()
    for d in session.exec(select(BeanDefect)).all():
        by_label_source[d.label_source] += 1
        if d.is_primary:
            by_primary[defect_name.get(d.defect_index, str(d.defect_index))] += 1

    not_good = session.exec(
        select(func.count()).select_from(Bean).where(Bean.is_good == False)  # noqa: E712
    ).one()

    # Integrity: beans without any view.
    beans_with_views = set(session.exec(select(BeanView.bean_id)).all())
    all_bean_ids = set(session.exec(select(Bean.id)).all())
    missing_views = len(all_bean_ids - beans_with_views)

    # License-blocked sources that nonetheless hold beans.
    blocked = []
    for source in session.exec(
        select(Source).where(Source.status == STATUS_LICENSE_UNVERIFIED)
    ).all():
        n = by_source.get(source.name, 0)
        if n:
            blocked.append((source.name, n))

    return {
        "total_beans": total_beans,
        "total_views": total_views,
        "total_defects": total_defects,
        "not_good": not_good,
        "missing_views": missing_views,
        "by_provenance": dict(by_provenance),
        "by_source": dict(by_source),
        "by_split": dict(by_split),
        "by_primary_class": dict(by_primary.most_common()),
        "by_label_source": dict(by_label_source),
        "license_blocked_with_beans": blocked,
    }


def print_audit(session: Session) -> dict:
    """Print a human-readable audit and return the report dict."""
    r = audit_report(session)
    print(f"beans={r['total_beans']}  views={r['total_views']}  defect-labels={r['total_defects']}")
    print(f"not-good (excluded from export): {r['not_good']}   missing-views: {r['missing_views']}")

    def _section(title: str, mapping: dict) -> None:
        print(f"\n{title}:")
        for k, v in mapping.items():
            print(f"  {k:<26} {v}")

    _section("by provenance", r["by_provenance"])
    _section("by source", r["by_source"])
    _section("by split", r["by_split"])
    _section("by primary defect class", r["by_primary_class"])
    _section("by label source", r["by_label_source"])

    if r["license_blocked_with_beans"]:
        print("\n⚠️  license-blocked sources holding beans (should not be exported):")
        for name, n in r["license_blocked_with_beans"]:
            print(f"  {name}: {n} beans")
    return r
