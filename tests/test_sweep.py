"""Tests for the backbone-sweep report writers (no training)."""

import csv

from almendra.bench.sweep import _bench_summary, _write_csv, _write_markdown


def _row(backbone: str = "mn3_small") -> dict:
    return {
        "backbone": backbone,
        "test_accuracy": 0.92,
        "test_macro_f1": 0.93,
        "missed_defect": 0.05,
        "float_size_mb": 4.06,
        "int8_size_mb": 1.20,
        "float_p50_ms": 2.1,
        "float_throughput": 470,
        "int8_p50_ms": 1.5,
        "int8_throughput": 650,
        "bench_provider": "CPUExecutionProvider",
    }


def test_bench_summary_prefers_cpu():
    latencies = {
        "CoreMLExecutionProvider": {"p50_ms": 9.0},
        "CPUExecutionProvider": {"p50_ms": 2.0},
    }
    stats, provider = _bench_summary(latencies)
    assert provider == "CPUExecutionProvider"
    assert stats["p50_ms"] == 2.0


def test_bench_summary_empty():
    assert _bench_summary({}) == (None, None)


def test_write_csv_roundtrip(tmp_path):
    path = tmp_path / "results.csv"
    rows = [_row("a"), _row("b")]
    _write_csv(rows, path)
    with path.open() as fh:
        loaded = list(csv.DictReader(fh))
    assert [r["backbone"] for r in loaded] == ["a", "b"]


def test_write_markdown_table(tmp_path):
    path = tmp_path / "pareto.md"
    _write_markdown([_row("a"), _row("b")], path, epochs=20)
    text = path.read_text()
    assert "Backbone sweep" in text
    assert "| a |" in text and "| b |" in text
    assert "CPUExecutionProvider" in text
