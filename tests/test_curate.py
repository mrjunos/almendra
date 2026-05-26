"""Curation tests — dedup, quality gate, lossy-label trust, export exclusion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

pytest.importorskip("sqlmodel")
pytest.importorskip("imagehash")
from sqlmodel import select  # noqa: E402

from almendra.datasets.manifest import BeanRecord, read_manifest, write_manifest  # noqa: E402
from almendra.db.catalog import get_engine, get_session, init_db  # noqa: E402
from almendra.db.curate import curate  # noqa: E402
from almendra.db.export import export_manifest  # noqa: E402
from almendra.db.migrate import migrate_manifest  # noqa: E402
from almendra.db.models import Bean, BeanDefect  # noqa: E402
from almendra.db.seed import seed_all  # noqa: E402

SRC = "roboflow_robusta_defects"  # a seeded source — lets the lossy rule match


def _save(root: Path, rel: str, arr: np.ndarray) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8)).save(path)


def _noise(seed: int, size: int = 96) -> np.ndarray:
    return np.random.RandomState(seed).randint(0, 256, (size, size, 3))


def _build(tmp_path: Path):
    """Create images + a manifest covering each curation case; return (root, manifest)."""
    root = tmp_path / "processed"
    img_a = _noise(1)
    cases = {
        f"{SRC}/sound/b0.png": img_a,
        f"{SRC}/sound/b1.png": img_a.copy(),  # exact duplicate of b0
        f"{SRC}/full_black/b2.png": _noise(2),
        f"{SRC}/immature/b3.png": _noise(4, size=20),  # too small
        f"{SRC}/immature/b4.png": np.full((64, 64, 3), 128),  # near-blank (std 0)
        f"{SRC}/defect_unspecified/b5.png": _noise(3),  # lossy mapping → trust lowered
    }
    for rel, arr in cases.items():
        _save(root, rel, arr)

    recs = [
        BeanRecord("b0", SRC, "sound", 0, "train", [f"{SRC}/sound/b0.png"]),
        BeanRecord("b1", SRC, "sound", 0, "train", [f"{SRC}/sound/b1.png"]),
        BeanRecord("b2", SRC, "full_black", 1, "train", [f"{SRC}/full_black/b2.png"]),
        BeanRecord("b3", SRC, "immature", 11, "train", [f"{SRC}/immature/b3.png"]),
        BeanRecord("b4", SRC, "immature", 11, "train", [f"{SRC}/immature/b4.png"]),
        BeanRecord(
            "b5", SRC, "defect_unspecified", 17, "train", [f"{SRC}/defect_unspecified/b5.png"]
        ),
    ]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(recs, manifest)
    return root, manifest


def test_curate_flags_and_export_excludes(tmp_path: Path):
    root, manifest = _build(tmp_path)
    engine = get_engine(":memory:")
    init_db(engine)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)

    with get_session(engine) as s:
        summary = curate(s, root=root)

    assert summary["duplicates_flagged"] == 1  # b1 is a copy of b0
    assert summary["too_small"] == 1  # b3
    assert summary["near_blank"] == 1  # b4
    assert summary["labels_downweighted"] == 1  # b5 (defect_unspecified ← Scorched)

    with get_session(engine) as s:
        not_good = {
            b.ext_id
            for b in s.exec(select(Bean).where(Bean.is_good == False)).all()  # noqa: E712
        }
        assert not_good == {"b1", "b3", "b4"}
        # b5's defect label trust was lowered below the dataset default.
        b5 = s.exec(select(Bean).where(Bean.ext_id == "b5")).first()
        bd = s.exec(select(BeanDefect).where(BeanDefect.bean_id == b5.id)).first()
        assert bd.trust == pytest.approx(0.2)

    out = tmp_path / "good.jsonl"
    with get_session(engine) as s:
        export_manifest(s, out, provenance_types=None)
    exported = {r.bean_id for r in read_manifest(out)}
    assert exported == {"b0", "b2", "b5"}  # duplicate + low-quality excluded


def test_curate_idempotent(tmp_path: Path):
    root, manifest = _build(tmp_path)
    engine = get_engine(":memory:")
    init_db(engine)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)
    with get_session(engine) as s:
        curate(s, root=root)
    with get_session(engine) as s:
        again = curate(s, root=root)
    assert again["duplicates_flagged"] == 0
    assert again["too_small"] == 0 and again["near_blank"] == 0
    assert again["labels_downweighted"] == 0


def test_dry_run_writes_nothing(tmp_path: Path):
    root, manifest = _build(tmp_path)
    engine = get_engine(":memory:")
    init_db(engine)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)
    with get_session(engine) as s:
        curate(s, root=root, dry_run=True)
    with get_session(engine) as s:
        not_good = s.exec(select(Bean).where(Bean.is_good == False)).all()  # noqa: E712
        assert not_good == []
