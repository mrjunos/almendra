"""Tests for the multi-label evaluation metrics."""

from almendra.eval.metrics import compute_metrics, missed_defect_rate, to_multihot


def test_perfect_predictions_score_one():
    y = to_multihot([[0], [1], [2], [0], [1]], num_classes=3)
    metrics = compute_metrics(y, y, num_classes=3)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["micro_f1"] == 1.0
    assert metrics["n_classes_present"] == 3


def test_macro_f1_ignores_absent_classes():
    # only classes 0 and 1 appear; the 18-class taxonomy must not dilute macro-F1
    y = to_multihot([[0], [1], [0], [1]], num_classes=18)
    metrics = compute_metrics(y, y, num_classes=18)
    assert metrics["macro_f1"] == 1.0
    assert metrics["n_classes_present"] == 2


def test_multi_label_bean_with_two_defects():
    # one bean is both class 1 and class 11 — exact match requires getting both
    y_true = to_multihot([[1, 11], [0]], num_classes=18)
    y_partial = to_multihot([[1], [0]], num_classes=18)  # misses class 11
    perfect = compute_metrics(y_true, y_true, num_classes=18)
    partial = compute_metrics(y_true, y_partial, num_classes=18)
    assert perfect["accuracy"] == 1.0
    assert partial["accuracy"] == 0.5  # one of two rows fully correct
    assert partial["per_class"][11]["recall"] == 0.0


def test_missed_defect_rate():
    # sound = 0; reject classes are everything else. 4 defective beans, 2 predicted clean.
    reject = list(range(1, 18))
    y_true = to_multihot([[1], [2], [3], [1]], num_classes=18)
    y_pred = to_multihot([[0], [2], [0], [1]], num_classes=18)
    assert missed_defect_rate(y_true, y_pred, reject) == 0.5


def test_missed_defect_rate_no_defects():
    reject = list(range(1, 18))
    y = to_multihot([[0], [0]], num_classes=18)
    assert missed_defect_rate(y, y, reject) == 0.0
