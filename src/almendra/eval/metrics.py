"""Multi-label classification metrics for the defect classifier.

A bean can carry several defects, so labels and predictions are **(N, C) binary
indicator** matrices (column = taxonomy defect index, including index 0 =
``sound``). ``macro_f1`` averages F1 over the classes actually present in the
targets — early data covers only some of the 18 classes, and averaging over
absent classes would understate performance.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np
from sklearn.metrics import precision_recall_fscore_support

# Probability threshold for turning sigmoid outputs into a 0/1 prediction.
DEFAULT_THRESHOLD = 0.5


def to_multihot(index_lists: Iterable[Sequence[int]], num_classes: int) -> np.ndarray:
    """Convert an iterable of defect-index lists into an (N, C) indicator matrix."""
    rows = list(index_lists)
    out = np.zeros((len(rows), num_classes), dtype=np.int64)
    for r, indices in enumerate(rows):
        for idx in indices:
            out[r, idx] = 1
    return out


def compute_metrics(y_true, y_pred, num_classes: int) -> dict:
    """Multi-label metrics from (N, C) indicator matrices.

    Returns exact-match (subset) ``accuracy``, ``macro_f1`` over present classes,
    ``micro_f1``, and a per-class precision/recall/F1/support breakdown.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    if y_true.ndim != 2 or y_pred.ndim != 2:
        raise ValueError("compute_metrics expects (N, C) multi-label indicator matrices")
    labels = list(range(num_classes))

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    present = [i for i in labels if support[i] > 0]
    macro_f1 = float(np.mean([f1[i] for i in present])) if present else 0.0
    _, _, micro_f1, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="micro", zero_division=0
    )
    exact_match = float((y_true == y_pred).all(axis=1).mean()) if len(y_true) else 0.0

    return {
        "accuracy": exact_match,  # exact-match (subset) accuracy
        "macro_f1": macro_f1,
        "micro_f1": float(micro_f1),
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


def missed_defect_rate(y_true, y_pred, reject_indices: Sequence[int]) -> float:
    """Fraction of truly-defective beans predicted as having no defect.

    The metric that matters most for a sorter: a defective bean is "missed" if
    none of its reject-worthy (defect) classes is predicted. ``reject_indices``
    are the taxonomy indices of the classes a bean is rejected for.
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    rej = list(reject_indices)
    if not rej or len(y_true) == 0:
        return 0.0
    true_defect = y_true[:, rej].any(axis=1)
    pred_defect = y_pred[:, rej].any(axis=1)
    if not true_defect.any():
        return 0.0
    missed = true_defect & ~pred_defect
    return float(missed.sum() / true_defect.sum())
