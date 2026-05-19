"""Multi-view bean dataset.

Each sample is one bean: a tensor of shape ``[V, C, H, W]`` stacking its views,
plus the integer defect label. ``V`` is fixed (``num_views``): a bean with fewer
views is padded by sampling its own views with replacement, with more views is
randomly subsampled.

``view_dropout`` (training only) randomly blanks views so the model tolerates a
variable view count at deployment — the "collect rich, deploy lean" principle.
For the single-view baseline (``num_views = 1``) it has no effect.
"""

from __future__ import annotations

import random
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from almendra.datasets.manifest import BeanRecord
from almendra.paths import processed_dir


class MultiViewBeanDataset(Dataset):
    def __init__(
        self,
        records: list[BeanRecord],
        transform,
        num_views: int = 1,
        view_dropout: float = 0.0,
        root: str | Path | None = None,
    ):
        self.records = list(records)
        self.transform = transform
        self.num_views = num_views
        self.view_dropout = view_dropout
        self.root = Path(root) if root is not None else processed_dir()

    def __len__(self) -> int:
        return len(self.records)

    def _pick_views(self, paths: list[str]) -> list[str]:
        """Return exactly `num_views` view paths (subsample or pad-with-resample)."""
        if len(paths) >= self.num_views:
            return random.sample(paths, self.num_views)
        return paths + random.choices(paths, k=self.num_views - len(paths))

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        record = self.records[idx]
        views = []
        for i, rel_path in enumerate(self._pick_views(record.views)):
            with Image.open(self.root / rel_path) as image:
                tensor = self.transform(image.convert("RGB"))
            # view-dropout: blank a view, but never the first (keep >=1 real view)
            if self.view_dropout and i > 0 and random.random() < self.view_dropout:
                tensor = torch.zeros_like(tensor)
            views.append(tensor)
        return torch.stack(views, dim=0), record.defect_index
