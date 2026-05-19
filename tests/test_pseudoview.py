"""Tests for pseudo-views and the multi-view dataset."""

import numpy as np
import torch
from PIL import Image

from almendra.datasets.manifest import BeanRecord
from almendra.datasets.multiview import MultiViewBeanDataset
from almendra.datasets.pseudoview import ORIENTATIONS, pseudo_view
from almendra.datasets.transforms import build_transforms


def _asymmetric_image(size: int = 64) -> Image.Image:
    """An image with no rotational symmetry, so orientations are distinguishable."""
    arr = np.zeros((size, size, 3), dtype=np.uint8)
    arr[: size // 3, :] = 200  # bright top stripe
    arr[:, : size // 4] = 120  # mid-grey left stripe
    return Image.fromarray(arr)


def test_pseudo_views_differ_by_orientation():
    image = _asymmetric_image()
    v0 = np.asarray(pseudo_view(image, 0))
    v1 = np.asarray(pseudo_view(image, 1))  # 90 deg
    v2 = np.asarray(pseudo_view(image, 2))  # 180 deg
    assert not np.array_equal(v0, v1)
    assert not np.array_equal(v0, v2)


def test_pseudo_view_index_wraps_around():
    image = _asymmetric_image()
    first = np.asarray(pseudo_view(image, 0))
    wrapped = np.asarray(pseudo_view(image, len(ORIENTATIONS)))
    assert np.array_equal(first, wrapped)


def _single_view_record(views=("bean.png",)) -> BeanRecord:
    return BeanRecord(
        bean_id="b1",
        source="s",
        defect_class="sound",
        defect_index=0,
        split="train",
        views=list(views),
    )


def test_multiview_dataset_with_pseudo_views(tmp_path):
    _asymmetric_image().save(tmp_path / "bean.png")
    transform = build_transforms(48, None, train=False)
    dataset = MultiViewBeanDataset(
        [_single_view_record()], transform, num_views=4, pseudo_views=True, root=tmp_path
    )
    views, label = dataset[0]
    assert views.shape == (4, 3, 48, 48)
    assert label == 0
    # the four pseudo-views are genuinely different orientations
    assert not torch.equal(views[0], views[1])


def test_multiview_dataset_single_view(tmp_path):
    _asymmetric_image().save(tmp_path / "bean.png")
    transform = build_transforms(48, None, train=False)
    dataset = MultiViewBeanDataset([_single_view_record()], transform, num_views=1, root=tmp_path)
    views, _ = dataset[0]
    assert views.shape == (1, 3, 48, 48)
