"""Tests for the dataset manifest."""

from almendra.datasets.manifest import BeanRecord, class_distribution, filter_split


def _rec(bean_id, defect_class, defect_index, split, n_views=1):
    return BeanRecord(
        bean_id=bean_id,
        source="src",
        defect_class=defect_class,
        defect_index=defect_index,
        split=split,
        views=[f"{bean_id}_{i}.png" for i in range(n_views)],
    )


def test_bean_record_json_round_trip():
    rec = _rec("b1", "full_black", 1, "train", n_views=3)
    assert BeanRecord.from_json(rec.to_json()) == rec


def test_write_then_read_manifest(tmp_path):
    from almendra.datasets.manifest import read_manifest, write_manifest

    records = [_rec("b1", "sound", 0, "train"), _rec("b2", "full_black", 1, "test")]
    path = tmp_path / "manifest.jsonl"
    write_manifest(records, path)
    assert read_manifest(path) == records


def test_filter_split():
    records = [_rec("b1", "sound", 0, "train"), _rec("b2", "sound", 0, "test")]
    assert [r.bean_id for r in filter_split(records, "train")] == ["b1"]


def test_class_distribution():
    records = [
        _rec("b1", "sound", 0, "train"),
        _rec("b2", "sound", 0, "train"),
        _rec("b3", "full_black", 1, "train"),
    ]
    assert class_distribution(records) == {"sound": 2, "full_black": 1}
