"""Tests for the canonical taxonomy schema."""

import pytest

from almendra.taxonomy import Taxonomy, get_taxonomy


def test_default_taxonomy_loads():
    tax = get_taxonomy()
    assert tax.num_defect_classes >= 2
    assert "sound" in tax.defect_classes


def test_indices_contiguous_and_ordered():
    tax = get_taxonomy()
    names = tax.class_names()
    for i, name in enumerate(names):
        assert tax.index_of(name) == i
        assert tax.name_of(i) == name


def test_sound_is_accepted_and_defect_free():
    tax = get_taxonomy()
    assert tax.is_accept("sound") is True
    assert tax.full_defect_equivalent("sound") == 0


def test_every_non_sound_class_is_a_rejected_defect():
    tax = get_taxonomy()
    for name, cls in tax.defect_classes.items():
        if name == "sound":
            continue
        assert cls.accept is False
        assert cls.full_defect_equivalent > 0


def test_categories_are_valid_and_partitioned():
    tax = get_taxonomy()
    assert tax.by_category(0) == [tax.defect_classes["sound"]]
    assert len(tax.by_category(1)) > 0  # SCA primary defects
    assert len(tax.by_category(2)) > 0  # SCA secondary defects


def test_validate_rejects_non_contiguous_indices():
    raw = {
        "schema_version": 1,
        "defect_classes": {
            "sound": {
                "index": 0,
                "category": 0,
                "accept": True,
                "full_defect_equivalent": 0,
                "description": "ok",
            },
            "full_black": {
                "index": 5,
                "category": 1,
                "accept": False,
                "full_defect_equivalent": 1,
                "description": "gap in indices",
            },
        },
    }
    with pytest.raises(ValueError, match="contiguous"):
        Taxonomy(raw)


def test_validate_requires_a_sound_class():
    raw = {
        "schema_version": 1,
        "defect_classes": {
            "full_black": {
                "index": 0,
                "category": 1,
                "accept": False,
                "full_defect_equivalent": 1,
                "description": "no sound class",
            },
        },
    }
    with pytest.raises(ValueError, match="sound"):
        Taxonomy(raw)
