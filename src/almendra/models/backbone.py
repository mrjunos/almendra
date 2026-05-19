"""Lightweight backbone registry.

A backbone is a feature extractor: an image batch ``[N, 3, H, W]`` becomes an
embedding ``[N, D]``. Backbones are swappable via ``configs/model/*.yaml``.

EfficientNet-Lite, GhostNet, ShuffleNetV2 and MobileOne are added via `timm` in
the Phase 5 sweep; the Phase 1 registry uses torchvision backbones.
"""

from __future__ import annotations

from torch import nn
from torchvision import models

# name -> (constructor, default ImageNet weights, feature-map channel count)
_REGISTRY = {
    "mobilenet_v3_small": (
        models.mobilenet_v3_small,
        models.MobileNet_V3_Small_Weights.IMAGENET1K_V1,
        576,
    ),
    "mobilenet_v3_large": (
        models.mobilenet_v3_large,
        models.MobileNet_V3_Large_Weights.IMAGENET1K_V1,
        960,
    ),
    "efficientnet_b0": (
        models.efficientnet_b0,
        models.EfficientNet_B0_Weights.IMAGENET1K_V1,
        1280,
    ),
}


class Backbone(nn.Module):
    """Feature extractor wrapping a torchvision backbone."""

    def __init__(self, name: str, pretrained: bool = True):
        super().__init__()
        if name not in _REGISTRY:
            raise ValueError(f"unknown backbone '{name}'; known: {sorted(_REGISTRY)}")
        constructor, weights, feature_dim = _REGISTRY[name]
        net = constructor(weights=weights if pretrained else None)
        self.features = net.features
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.feature_dim = feature_dim

    def forward(self, x):  # [N, 3, H, W] -> [N, D]
        x = self.features(x)
        return self.pool(x).flatten(1)


def list_backbones() -> list[str]:
    return sorted(_REGISTRY)
