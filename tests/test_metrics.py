"""Tests for the evaluation metrics."""

import numpy as np

from almendra.eval.metrics import compute_metrics, confusion, missed_defect_rate


def test_perfect_predictions_score_one():
    targets = np.array([0, 1, 2, 0, 1])
    metrics = compute_metrics(targets, targets, num_classes=3)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["n_classes_present"] == 3


def test_macro_f1_ignores_absent_classes():
    # only classes 0 and 1 appear; the 18-class taxonomy must not dilute macro-F1
    targets = np.array([0, 1, 0, 1])
    metrics = compute_metrics(targets, targets, num_classes=18)
    assert metrics["macro_f1"] == 1.0
    assert metrics["n_classes_present"] == 2


def test_missed_defect_rate():
    # sound = class 0; four true defects, two predicted as sound
    targets = np.array([1, 2, 3, 1])
    preds = np.array([0, 2, 0, 1])
    assert missed_defect_rate(targets, preds, sound_index=0) == 0.5


def test_missed_defect_rate_no_defects():
    assert missed_defect_rate(np.array([0, 0]), np.array([0, 0]), sound_index=0) == 0.0


def test_confusion_matrix_shape():
    targets = np.array([0, 1, 2])
    assert confusion(targets, targets, num_classes=3).shape == (3, 3)
