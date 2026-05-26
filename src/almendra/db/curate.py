"""Curation passes — keep only good data.

Three independent passes, all idempotent and all writing their verdict into the
catalog (no files are deleted):

1. **dedup** — perceptual-hash near-duplicate detection; keeps one bean per
   cluster, flags the rest ``is_good=False``.
2. **quality** — flags crops that are too small or near-blank (low pixel
   variance) as ``is_good=False``.
3. **lossy labels** — lowers ``trust`` on defect labels that came from a
   documented lossy source mapping (so they stop dominating training without
   being thrown away).

The reason is recorded in ``Bean.notes`` (prefix ``curation:``) so ``db audit``
can break the exclusions down, and so a human can review and reverse them.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from sqlmodel import Session, select

from almendra.db.models import Bean, BeanDefect, BeanView, Lot, Source
from almendra.paths import processed_dir
from almendra.taxonomy import get_taxonomy

_NOTE_PREFIX = "curation:"

# Documented lossy mappings: (source, canonical defect, new trust, reason).
# Lowering trust lets `db export-manifest --min-trust` drop or down-weight them
# without deleting the beans. See docs/datasheets/.
DEFAULT_LOSSY_RULES: list[tuple[str, str, float, str]] = [
    ("roboflow_robusta_defects", "defect_unspecified", 0.2, "Scorched→defect_unspecified"),
    ("roboflow_robusta_defects", "hull_husk", 0.3, "Empty→hull_husk (questionable)"),
]


def _set_not_good(bean: Bean, reason: str) -> None:
    bean.is_good = False
    note = f"{_NOTE_PREFIX} {reason}"
    bean.notes = note if not bean.notes else f"{bean.notes}; {note}"


def _first_view_path(session: Session, bean_id: int, root: Path) -> Path | None:
    view = session.exec(
        select(BeanView).where(BeanView.bean_id == bean_id).order_by(BeanView.view_index)
    ).first()
    if view is None:
        return None
    p = Path(view.path)
    return p if p.is_absolute() else root / p


def flag_duplicates(
    session: Session, root: Path | None = None, threshold: int = 4, dry_run: bool = False
) -> dict:
    """Flag near-duplicate beans (Hamming distance <= ``threshold``) as not-good.

    Greedy: each bean is compared against the kept representatives; the first
    bean of a cluster is kept, later ones are flagged ``duplicate of <id>``.
    O(n·k) in the number of representatives — fine at current scale; swap in an
    LSH/BK-tree index here if the catalog grows large.
    """
    import imagehash

    root = root or processed_dir()
    beans = session.exec(select(Bean).where(Bean.is_good == True).order_by(Bean.id)).all()  # noqa: E712

    reps: list[tuple[object, int]] = []  # (hash, bean_id)
    flagged = 0
    missing = 0
    for bean in beans:
        path = _first_view_path(session, bean.id, root)
        if path is None or not path.is_file():
            missing += 1
            continue
        with Image.open(path) as im:
            h = imagehash.phash(im.convert("RGB"))
        match = next((rid for rh, rid in reps if (h - rh) <= threshold), None)
        if match is None:
            reps.append((h, bean.id))
        else:
            flagged += 1
            if not dry_run:
                _set_not_good(bean, f"duplicate of {match}")
                session.add(bean)
    return {"duplicates_flagged": flagged, "kept": len(reps), "missing_images": missing}


def flag_low_quality(
    session: Session,
    root: Path | None = None,
    min_px: int = 48,
    min_stddev: float = 6.0,
    dry_run: bool = False,
) -> dict:
    """Flag crops that are too small or near-blank (low pixel std-dev)."""
    root = root or processed_dir()
    beans = session.exec(select(Bean).where(Bean.is_good == True).order_by(Bean.id)).all()  # noqa: E712

    tiny = 0
    blank = 0
    for bean in beans:
        path = _first_view_path(session, bean.id, root)
        if path is None or not path.is_file():
            continue
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            w, hgt = rgb.size
            arr = np.asarray(rgb.convert("L"), dtype=np.float32)
        if min(w, hgt) < min_px:
            tiny += 1
            if not dry_run:
                _set_not_good(bean, f"too small ({w}x{hgt})")
                session.add(bean)
        elif float(arr.std()) < min_stddev:
            blank += 1
            if not dry_run:
                _set_not_good(bean, f"near-blank (std={arr.std():.1f})")
                session.add(bean)
    return {"too_small": tiny, "near_blank": blank}


def flag_lossy_labels(
    session: Session, rules: list[tuple[str, str, float, str]] | None = None, dry_run: bool = False
) -> dict:
    """Lower trust on defect labels from documented lossy source mappings."""
    rules = rules if rules is not None else DEFAULT_LOSSY_RULES
    taxonomy = get_taxonomy()
    updated = 0
    for source_name, defect_name, new_trust, reason in rules:
        if defect_name not in taxonomy.defect_classes:
            continue
        idx = taxonomy.index_of(defect_name)
        rows = session.exec(
            select(BeanDefect)
            .join(Bean, BeanDefect.bean_id == Bean.id)
            .join(Lot, Bean.lot_id == Lot.id)
            .join(Source, Lot.source_id == Source.id)
            .where(Source.name == source_name, BeanDefect.defect_index == idx)
        ).all()
        for bd in rows:
            if bd.trust > new_trust:
                updated += 1
                if not dry_run:
                    bd.trust = new_trust
                    bd.labeler = f"curation:lossy ({reason})"
                    session.add(bd)
    return {"labels_downweighted": updated}


def curate(
    session: Session,
    root: Path | None = None,
    *,
    dedup_threshold: int = 4,
    min_px: int = 48,
    min_stddev: float = 6.0,
    dry_run: bool = False,
) -> dict:
    """Run every curation pass; return a merged summary dict."""
    summary: dict = {}
    summary.update(flag_duplicates(session, root, dedup_threshold, dry_run))
    summary.update(flag_low_quality(session, root, min_px, min_stddev, dry_run))
    summary.update(flag_lossy_labels(session, dry_run=dry_run))
    summary["dry_run"] = dry_run
    return summary
