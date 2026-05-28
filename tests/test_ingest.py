"""Tests for the dataset ingesters (focus: the new classification ingester).

The COCO ingester is exercised end-to-end on the real Roboflow dump in dev; the
classification path is the new piece and needs unit coverage.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from almendra.datasets.ingest import (
    _hash_split,
    _ingest_classification_source,
    _resolve_classification_labels,
)
from almendra.taxonomy import get_taxonomy

SRC = "synth_classification"


def _save(path: Path, seed: int = 0, size: int = 64) -> None:
    """Write a tiny deterministic PNG so the ingester has something to open."""
    arr = np.random.RandomState(seed).randint(0, 256, (size, size, 3), dtype=np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(path)


def _flat_layout(root: Path, classes: dict[str, int]) -> None:
    """``classes`` = mapping of source class name → number of images to write."""
    for cls, n in classes.items():
        for i in range(n):
            _save(root / SRC / cls / f"img_{i}.png", seed=hash((cls, i)) % 1000)


def test_classification_flat_layout_produces_one_record_per_image(tmp_path: Path):
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    _flat_layout(raw, {"good": 5, "black": 4, "broken": 3})

    cfg = {
        "class_map": {
            "good": "sound",
            "black": "full_black",
            "broken": "broken_chipped_cut",
        }
    }
    records = _ingest_classification_source(
        SRC, cfg, get_taxonomy(), out_root=out, src_root=raw / SRC
    )

    assert len(records) == 12
    by_class = {}
    for r in records:
        by_class.setdefault(r.defect_class, 0)
        by_class[r.defect_class] += 1
        # Image was copied into processed under the canonical class dir.
        assert (out / Path(r.views[0])).is_file()
        assert r.source == SRC
    assert by_class == {"sound": 5, "full_black": 4, "broken_chipped_cut": 3}


def test_classification_skips_unmapped_and_unknown_canonical(tmp_path: Path):
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    _flat_layout(raw, {"good": 2, "mystery": 3, "broken": 2})

    cfg = {
        "class_map": {
            "good": "sound",
            "mystery": "not_a_taxonomy_class",  # canonical not in taxonomy → skip
            "broken": "broken_chipped_cut",
            # "weird" is not present in class_map at all → would be skipped if it appeared
        }
    }
    records = _ingest_classification_source(
        SRC, cfg, get_taxonomy(), out_root=out, src_root=raw / SRC
    )
    classes = {r.defect_class for r in records}
    assert classes == {"sound", "broken_chipped_cut"}
    assert len(records) == 4


def test_classification_split_subdirs_are_honoured(tmp_path: Path):
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    # Roboflow exports use "valid" — must be mapped to canonical "val".
    for split in ("train", "valid", "test"):
        for i in range(3):
            _save(raw / SRC / split / "good" / f"img_{i}.png", seed=i)

    cfg = {"class_map": {"good": "sound"}}
    records = _ingest_classification_source(
        SRC, cfg, get_taxonomy(), out_root=out, src_root=raw / SRC
    )
    splits = sorted(r.split for r in records)
    assert splits.count("train") == 3
    assert splits.count("val") == 3  # "valid" → "val"
    assert splits.count("test") == 3


def test_classification_dict_class_map_sets_morphology(tmp_path: Path):
    """USK-COFFEE style class_map carries both defect + morphology."""
    raw = tmp_path / "raw"
    out = tmp_path / "processed"
    _flat_layout(raw, {"peaberry": 2, "premium": 2})

    cfg = {
        "class_map": {
            "peaberry": {"defect": "sound", "morphology": "peaberry"},
            "premium": {"defect": "sound", "morphology": "normal"},
        }
    }
    records = _ingest_classification_source(
        SRC, cfg, get_taxonomy(), out_root=out, src_root=raw / SRC
    )
    by_morph = {r.morphology for r in records if r.defect_class == "sound"}
    assert by_morph == {"peaberry", "normal"}
    # Sanity: still tagged sound for the defect axis.
    assert all(r.defect_class == "sound" for r in records)


def test_hash_split_is_deterministic_and_respects_ratios():
    ratios = {"train": 0.70, "val": 0.15, "test": 0.15}
    names = [f"img_{i}.png" for i in range(1000)]
    counts = {"train": 0, "val": 0, "test": 0}
    for n in names:
        counts[_hash_split(n, ratios)] += 1
    # uniform hash → counts within ±5% of the requested ratios
    for split, expected in (("train", 700), ("val", 150), ("test", 150)):
        assert abs(counts[split] - expected) < 50, counts
    # determinism
    assert _hash_split("a.png", ratios) == _hash_split("a.png", ratios)


def test_resolve_classification_labels_shapes():
    assert _resolve_classification_labels("sound") == {"defect": "sound", "morphology": None}
    assert _resolve_classification_labels({"defect": "sound", "morphology": "peaberry"}) == {
        "defect": "sound",
        "morphology": "peaberry",
    }
    assert _resolve_classification_labels(None) is None
    assert _resolve_classification_labels(42) is None
