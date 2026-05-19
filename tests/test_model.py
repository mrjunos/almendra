"""Tests for the multi-view model."""

import torch

from almendra.models.backbone import list_backbones
from almendra.models.classifier import MultiViewClassifier
from almendra.models.fusion import build_fusion


def test_forward_single_view():
    model = MultiViewClassifier("mobilenet_v3_small", num_classes=18, pretrained=False)
    out = model(torch.randn(2, 1, 3, 96, 96))
    assert out.shape == (2, 18)


def test_forward_multi_view():
    model = MultiViewClassifier(
        "mobilenet_v3_small", num_classes=18, fusion="attention", pretrained=False
    )
    out = model(torch.randn(2, 5, 3, 96, 96))
    assert out.shape == (2, 18)


def test_fusion_heads_preserve_shape():
    x = torch.randn(3, 4, 16)  # [B, V, D]
    for name in ("mean", "max", "attention"):
        assert build_fusion(name, 16)(x).shape == (3, 16)


def test_registry_lists_baseline_backbone():
    assert "mobilenet_v3_small" in list_backbones()
