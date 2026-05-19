"""Classification metrics for the defect classifier.

`macro_f1` averages F1 over the classes actually present in the targets — early
data covers only some of the 18 taxonomy classes, and averaging over absent
classes would understate performance misleadingly.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


def compute_metrics(targets, preds, num_classes: int) -> dict:
    """Accuracy, macro-F1 (over present classes), and a per-class breakdown."""
    targets = np.asarray(targets)
    preds = np.asarray(preds)
    labels = list(range(num_classes))

    precision, recall, f1, support = precision_recall_fscore_support(
        targets, preds, labels=labels, zero_division=0
    )
    present = [i for i in labels if support[i] > 0]
    accuracy = float((targets == preds).mean()) if targets.size else 0.0
    macro_f1 = float(np.mean([f1[i] for i in present])) if present else 0.0

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "n_classes_present": len(present),
        "per_class": {
            i: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i in labels
        },
    }


def missed_defect_rate(targets, preds, sound_index: int) -> float:
    """Fraction of true defects that were classified as `sound` — the metric
    that matters most for a sorter (a defect that slips through)."""
    targets = np.asarray(targets)
    preds = np.asarray(preds)
    is_defect = targets != sound_index
    if not is_defect.any():
        return 0.0
    missed = is_defect & (preds == sound_index)
    return float(missed.sum() / is_defect.sum())


def confusion(targets, preds, num_classes: int) -> np.ndarray:
    return confusion_matrix(targets, preds, labels=list(range(num_classes)))
