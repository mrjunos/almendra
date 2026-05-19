"""Multi-view fusion heads.

Each head combines per-view embeddings ``[B, V, D]`` into one per-bean vector
``[B, D]``. ``attention`` is the default — it lets the model weight the views
that actually show a defect.
"""

from __future__ import annotations

import torch
from torch import nn


class MeanFusion(nn.Module):
    def forward(self, x):  # [B, V, D] -> [B, D]
        return x.mean(dim=1)


class MaxFusion(nn.Module):
    def forward(self, x):  # [B, V, D] -> [B, D]
        return x.max(dim=1).values


class AttentionFusion(nn.Module):
    """Attention pooling: a learned scorer weights each view, then sums."""

    def __init__(self, dim: int, hidden: int = 128):
        super().__init__()
        self.score = nn.Sequential(
            nn.Linear(dim, hidden),
            nn.Tanh(),
            nn.Linear(hidden, 1),
        )

    def forward(self, x):  # [B, V, D] -> [B, D]
        weights = torch.softmax(self.score(x).squeeze(-1), dim=1)  # [B, V]
        return (x * weights.unsqueeze(-1)).sum(dim=1)


class GatedAttentionFusion(nn.Module):
    """Gated attention pooling (Ilse et al., 2018).

    A sigmoid gating branch multiplies the tanh feature branch, letting the model
    suppress uninformative views more sharply than plain attention pooling.
    """

    def __init__(self, dim: int, hidden: int = 128):
        super().__init__()
        self.feature = nn.Linear(dim, hidden)
        self.gate = nn.Linear(dim, hidden)
        self.score = nn.Linear(hidden, 1)

    def forward(self, x):  # [B, V, D] -> [B, D]
        attended = torch.tanh(self.feature(x)) * torch.sigmoid(self.gate(x))
        weights = torch.softmax(self.score(attended).squeeze(-1), dim=1)  # [B, V]
        return (x * weights.unsqueeze(-1)).sum(dim=1)


def build_fusion(name: str, dim: int) -> nn.Module:
    if name == "mean":
        return MeanFusion()
    if name == "max":
        return MaxFusion()
    if name == "attention":
        return AttentionFusion(dim)
    if name == "gated":
        return GatedAttentionFusion(dim)
    raise ValueError(f"unknown fusion '{name}'; expected mean | max | attention | gated")
