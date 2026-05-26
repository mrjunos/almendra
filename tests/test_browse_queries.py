"""Tests for the Data Browser read queries (filters, pagination, detail)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sqlmodel")

from almendra.datasets.manifest import BeanRecord, write_manifest  # noqa: E402
from almendra.db.catalog import get_engine, get_session, init_db  # noqa: E402
from almendra.db.migrate import migrate_manifest  # noqa: E402
from almendra.db.queries import (  # noqa: E402
    BeanFilters,
    bean_detail,
    distinct_sources,
    query_page,
)
from almendra.db.seed import seed_all  # noqa: E402

SRC = "roboflow_robusta_defects"


def _engine_with_data(tmp_path: Path):
    recs = [
        BeanRecord("b0", SRC, "sound", 0, "train", [f"{SRC}/sound/b0.png"]),
        BeanRecord("b1", SRC, "full_black", 1, "val", [f"{SRC}/full_black/b1.png"]),
        BeanRecord("b2", SRC, "immature", 11, "test", [f"{SRC}/immature/b2.png"]),
    ]
    manifest = tmp_path / "manifest.jsonl"
    write_manifest(recs, manifest)
    engine = get_engine(":memory:")
    init_db(engine)
    with get_session(engine) as s:
        seed_all(s)
        migrate_manifest(s, manifest)
    return engine


def test_distinct_sources_and_unfiltered_count(tmp_path: Path):
    engine = _engine_with_data(tmp_path)
    with get_session(engine) as s:
        assert SRC in distinct_sources(s)
        total, rows = query_page(s, BeanFilters(), limit=10)
        assert total == 3 and len(rows) == 3


def test_filter_by_class_and_split(tmp_path: Path):
    engine = _engine_with_data(tmp_path)
    with get_session(engine) as s:
        total, rows = query_page(s, BeanFilters(primary_defect="full_black"))
        assert total == 1 and rows[0].ext_id == "b1"
        total, _ = query_page(s, BeanFilters(split="test"))
        assert total == 1


def test_pagination(tmp_path: Path):
    engine = _engine_with_data(tmp_path)
    with get_session(engine) as s:
        total, page1 = query_page(s, BeanFilters(), limit=2, offset=0)
        _, page2 = query_page(s, BeanFilters(), limit=2, offset=2)
        assert total == 3 and len(page1) == 2 and len(page2) == 1
        assert {r.ext_id for r in page1}.isdisjoint({r.ext_id for r in page2})


def test_bean_detail(tmp_path: Path):
    engine = _engine_with_data(tmp_path)
    with get_session(engine) as s:
        _, rows = query_page(s, BeanFilters(primary_defect="immature"))
        detail = bean_detail(s, rows[0].id)
    assert detail.ext_id == "b2"
    assert detail.lot["source"] == SRC
    assert any(d["class"] == "immature" and d["primary"] for d in detail.defects)
