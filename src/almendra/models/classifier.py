"""Multi-view bean classifier: shared backbone -> fusion -> defect head.

All views of a bean pass through the *same* backbone (shared weights), which
also lets every view of every in-flight bean run as one batched tensor — the
basis of the "model is never the bottleneck" speed argument.
"""

from __future__ import annotations

from torch import nn

from almendra.models.backbone import Backbone
from almendra.models.fusion import build_fusion


class MultiViewClassifier(nn.Module):
    def __init__(
        self,
        backbone_name: str,
        num_classes: int,
        fusion: str = "attention",
        pretrained: bool = True,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.backbone = Backbone(backbone_name, pretrained=pretrained)
        dim = self.backbone.feature_dim
        self.fusion = build_fusion(fusion, dim)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(dim, num_classes))
        self.num_classes = num_classes

    def forward(self, x):  # x: [B, V, C, H, W] -> logits [B, num_classes]
        batch, views = x.shape[:2]
        x = x.flatten(0, 1)  # [B*V, C, H, W] — shared backbone, one batch
        embeddings = self.backbone(x).view(batch, views, -1)  # [B, V, D]
        return self.head(self.fusion(embeddings))  # [B, num_classes]


def build_model(model_cfg, num_classes: int) -> MultiViewClassifier:
    """Build the classifier from a `configs/model/*.yaml` config block."""
    return MultiViewClassifier(
        backbone_name=model_cfg.backbone,
        num_classes=num_classes,
        fusion=model_cfg.fusion,
        pretrained=model_cfg.get("pretrained", True),
        dropout=model_cfg.get("dropout", 0.2),
    )
