"""Read/write the live-metrics JSONL file shared by training and the UI.

Protocol: one JSON object per line. ``event`` is ``start``, ``epoch``, or
``done``. The training loop writes; the UI tails. Anything that can write the
file in this format works with the UI — there's no in-process coupling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LiveMetrics:
    """Snapshot of a training run, reconstructed from its JSONL file."""

    epochs_total: int
    backbone: str
    epoch: list[int]
    train_loss: list[float]
    val_macro_f1: list[float]
    val_accuracy: list[float]
    done: bool
    best_val_macro_f1: float | None

    @property
    def epochs_completed(self) -> int:
        return len(self.epoch)

    @property
    def progress(self) -> float:
        if self.epochs_total <= 0:
            return 0.0
        return min(1.0, self.epochs_completed / self.epochs_total)


def read_live_metrics(path: str | Path) -> LiveMetrics:
    """Parse the JSONL file written by the training loop. Missing/empty -> defaults."""
    path = Path(path)
    epochs_total = 0
    backbone = ""
    epoch: list[int] = []
    train_loss: list[float] = []
    val_macro_f1: list[float] = []
    val_accuracy: list[float] = []
    done = False
    best: float | None = None

    if not path.is_file():
        return LiveMetrics(0, "", [], [], [], [], False, None)

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event = payload.get("event")
            if event == "start":
                epochs_total = int(payload.get("epochs", 0))
                backbone = str(payload.get("backbone", ""))
            elif event == "epoch":
                epoch.append(int(payload["epoch"]))
                train_loss.append(float(payload["train_loss"]))
                val_macro_f1.append(float(payload["val_macro_f1"]))
                val_accuracy.append(float(payload["val_accuracy"]))
                epochs_total = max(epochs_total, int(payload.get("epochs", epochs_total)))
            elif event == "done":
                done = True
                if "best_val_macro_f1" in payload:
                    best = float(payload["best_val_macro_f1"])
    return LiveMetrics(
        epochs_total, backbone, epoch, train_loss, val_macro_f1, val_accuracy, done, best
    )
