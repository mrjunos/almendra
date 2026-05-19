"""Multi-view bean dataset.

Each sample is one bean: a tensor of shape ``[V, C, H, W]`` stacking its views,
plus the integer defect label. ``V`` is fixed (``num_views``): a bean with fewer
views is padded by sampling its own views with replacement, with more views is
randomly subsampled.

``view_dropout`` (training only) randomly blanks views so the model tolerates a
variable view count at deployment — the "collect rich, deploy lean" principle.
For the single-view baseline (``num_views = 1``) it has no effect.

When ``pseudo_views`` is set, each view is a deterministic orientation of the
bean's real image(s) — an honest stand-in for real multi-view data while the
tray capture rig has not yet produced any (see ``almendra.datasets.pseudoview``).
"""

from __future__ import annotations

import random
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from almendra.datasets.manifest import BeanRecord
from almendra.datasets.pseudoview import pseudo_view
from almendra.paths import processed_dir


class MultiViewBeanDataset(Dataset):
    def __init__(
        self,
        records: list[BeanRecord],
        transform,
        num_views: int = 1,
        view_dropout: float = 0.0,
        pseudo_views: bool = False,
        root: str | Path | None = None,
    ):
        self.records = list(records)
        self.transform = transform
        self.num_views = num_views
        self.view_dropout = view_dropout
        self.pseudo_views = pseudo_views
        self.root = Path(root) if root is not None else processed_dir()

    def __len__(self) -> int:
        return len(self.records)

    def _pick_views(self, paths: list[str]) -> list[str]:
        """Return exactly `num_views` view paths (subsample or pad-with-resample)."""
        if len(paths) >= self.num_views:
            return random.sample(paths, self.num_views)
        return paths + random.choices(paths, k=self.num_views - len(paths))

    def _view_sources(self, record: BeanRecord) -> list[str]:
        """The `num_views` view paths to load for a bean."""
        if self.pseudo_views:
            # Each view is a deterministic orientation of one of the real views.
            return [record.views[i % len(record.views)] for i in range(self.num_views)]
        return self._pick_views(record.views)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        record = self.records[idx]
        views = []
        for i, rel_path in enumerate(self._view_sources(record)):
            with Image.open(self.root / rel_path) as handle:
                image = handle.convert("RGB")
            if self.pseudo_views:
                image = pseudo_view(image, i)
            tensor = self.transform(image)
            # view-dropout: blank a view, but never the first (keep >=1 real view)
            if self.view_dropout and i > 0 and random.random() < self.view_dropout:
                tensor = torch.zeros_like(tensor)
            views.append(tensor)
        return torch.stack(views, dim=0), record.defect_index
