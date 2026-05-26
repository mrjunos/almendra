"""Catalog tests — schema/seed, manifest migration, and gated export."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sqlmodel")
from sqlmodel import select  # noqa: E402

from almendra.datasets.manifest import BeanRecord, read_manifest, write_manifest  # noqa: E402
from almendra.db.catalog import get_engine, get_session, init_db  # noqa: E402
from almendra.db.export import export_manifest  # noqa: E402
from almendra.db.migrate import migrate_manifest  # noqa: E402
from almendra.db.models import (  # noqa: E402
    LABEL_HUMAN,
    PROVENANCE_PRIVATE,
    Bean,
    BeanDefect,
    BeanView,
    DefectClass,
    Lot,
    Source,
)
from almendra.db.seed import seed_all  # noqa: E402
from almendra.taxonomy import get_taxonomy  # noqa: E402


def _engine():
    engine = get_engine(":memory:")
    init_db(engine)
    return engine


def _tiny_manifest(tmp_path: Path) -> Path:
    src = "roboflow_robusta_defects"
    recs = [
        BeanRecord("b0", src, "sound", 0, "train", [f"{src}/sound/b0.png"]),
        BeanRecord("b1", src, "full_black", 1, "val", [f"{src}/full_black/b1.png"]),
        BeanRecord("b2", src, "immature", 11, "test", [f"{src}/immature/b2.png"]),
    ]
    path = tmp_path / "manifest.jsonl"
    write_manifest(recs, path)
    return path


def test_seed_counts_and_blocked_source():
    engine = _engine()
    with get_session(engine) as s:
        seed_all(s)
    with get_session(engine) as s:
        assert len(s.exec(select(DefectClass)).all()) == get_taxonomy().num_defect_classes
        sources = s.exec(select(Source)).all()
        assert {x.name for x in sources} >= {"roboflow_robusta_defects", "kaggle_17defects"}
        assert any(x.status == "license_unverified" for x in sources)


def test_migrate_counts_and_idempotent(tmp_path: Path):
    engine = _engine()
    manifest = _tiny_manifest(tmp_path)
    with get_session(engine) as s:
        seed_all(s)
        counts = migrate_manifest(s, manifest)
    assert counts["beans"] == 3 and counts["views"] == 3 and counts["defects"] == 3
    with get_session(engine) as s:
        again = migrate_manifest(s, manifest)
    assert again["beans"] == 0 and again["skipped"] == 3


def test_export_roundtrip(tmp_path: Path):
    engine = _engine()
    manifest = _tiny_manifest(tmp_path)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)
    out = tmp_path / "out.jsonl"
    with get_session(engine) as s:
        export_manifest(s, out, provenance_types=None)
    by_id = {r.bean_id: r for r in read_manifest(out)}
    assert set(by_id) == {"b0", "b1", "b2"}
    assert by_id["b1"].defect_class == "full_black" and by_id["b1"].defects == [1]
    assert by_id["b0"].defects == [0]  # sound is stored as an explicit label


def test_export_gates_good_and_provenance(tmp_path: Path):
    engine = _engine()
    manifest = _tiny_manifest(tmp_path)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)
        b0 = s.exec(select(Bean).where(Bean.ext_id == "b0")).first()
        b0.is_good = False  # quality gate should drop it
        s.add(b0)

    good = tmp_path / "good.jsonl"
    with get_session(engine) as s:
        export_manifest(s, good, provenance_types=None, good_only=True)
    assert {r.bean_id for r in read_manifest(good)} == {"b1", "b2"}

    # Add a private bean; default export (public-only) must exclude it.
    with get_session(engine) as s:
        src = s.exec(select(Source).where(Source.name == "roboflow_robusta_defects")).first()
        priv = Lot(source_id=src.id, name="priv", provenance_type=PROVENANCE_PRIVATE)
        s.add(priv)
        s.flush()
        pb = Bean(lot_id=priv.id, ext_id="p0", split="train", is_good=True)
        s.add(pb)
        s.flush()
        s.add(BeanView(bean_id=pb.id, path="priv/p0.png"))
        s.add(
            BeanDefect(
                bean_id=pb.id, defect_index=1, is_primary=True, label_source=LABEL_HUMAN, trust=1.0
            )
        )

    pub = tmp_path / "pub.jsonl"
    with get_session(engine) as s:
        export_manifest(s, pub)  # default provenance_types=("public_dataset",)
    assert "p0" not in {r.bean_id for r in read_manifest(pub)}

    allp = tmp_path / "all.jsonl"
    with get_session(engine) as s:
        export_manifest(s, allp, provenance_types=None, good_only=True)
    assert "p0" in {r.bean_id for r in read_manifest(allp)}


def test_beanrecord_backcompat_legacy_manifest(tmp_path: Path):
    """A legacy record without `defects` still loads (defects defaults to [])."""
    line = (
        '{"bean_id":"x","source":"s","defect_class":"sound","defect_index":0,'
        '"split":"train","views":["a.png"]}'
    )
    path = tmp_path / "old.jsonl"
    path.write_text(line + "\n")
    rec = read_manifest(path)[0]
    assert rec.defects == [] and rec.defect_index == 0
