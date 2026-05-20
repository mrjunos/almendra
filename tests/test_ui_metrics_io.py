"""Tests for the live-metrics JSONL file protocol shared by training and the UI."""

from __future__ import annotations

import json
from pathlib import Path

from almendra.ui.metrics_io import read_live_metrics


def _write(path: Path, lines: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")


def test_missing_file_returns_zeroed_snapshot(tmp_path: Path) -> None:
    snap = read_live_metrics(tmp_path / "nope.jsonl")
    assert snap.epochs_total == 0
    assert snap.epochs_completed == 0
    assert snap.progress == 0.0
    assert not snap.done


def test_start_then_epochs_then_done(tmp_path: Path) -> None:
    path = tmp_path / "live_metrics.jsonl"
    _write(
        path,
        [
            {"event": "start", "epochs": 3, "backbone": "mobilenet_v3_small"},
            {
                "event": "epoch",
                "epoch": 1,
                "epochs": 3,
                "train_loss": 1.0,
                "val_macro_f1": 0.3,
                "val_accuracy": 0.4,
            },
            {
                "event": "epoch",
                "epoch": 2,
                "epochs": 3,
                "train_loss": 0.6,
                "val_macro_f1": 0.6,
                "val_accuracy": 0.7,
            },
            {"event": "done", "best_val_macro_f1": 0.6},
        ],
    )
    snap = read_live_metrics(path)
    assert snap.backbone == "mobilenet_v3_small"
    assert snap.epochs_total == 3
    assert snap.epochs_completed == 2
    assert snap.progress > 0.6
    assert snap.train_loss == [1.0, 0.6]
    assert snap.val_macro_f1 == [0.3, 0.6]
    assert snap.done
    assert snap.best_val_macro_f1 == 0.6


def test_malformed_lines_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "x.jsonl"
    path.write_text(
        "\n"
        "this is not json\n"
        + json.dumps({"event": "start", "epochs": 1, "backbone": "x"})
        + "\n"
        + json.dumps(
            {
                "event": "epoch",
                "epoch": 1,
                "epochs": 1,
                "train_loss": 0.5,
                "val_macro_f1": 0.5,
                "val_accuracy": 0.5,
            }
        )
        + "\n"
    )
    snap = read_live_metrics(path)
    assert snap.epochs_completed == 1
    assert snap.val_macro_f1 == [0.5]
