"""Synthetic-image tests for the gridded-tray segmentation pipeline.

Each test renders a synthetic tray photo — real ArUco corner markers plus
ellipse "beans" — so the pipeline is exercised without needing real photographs.
"""

import cv2
import numpy as np
import pytest

from almendra.datasets.tray import (
    TrayError,
    TraySpec,
    extract_beans,
    pair_sides,
    rectify,
    well_centres,
)


def _make_tray(spec: TraySpec, occupied: set[tuple[int, int]]) -> np.ndarray:
    """Render a synthetic tray photo: ArUco corner markers + ellipse beans."""
    n = spec.canvas_px
    photo = np.full((n, n, 3), (180, 70, 200), dtype=np.uint8)  # magenta background
    inset, msize, pad = 200, 160, 50

    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(getattr(aruco, spec.marker_dict))
    corners = {
        0: (inset, inset),
        1: (n - inset, inset),
        2: (n - inset, n - inset),
        3: (inset, n - inset),
    }
    for marker_id, (mx, my) in corners.items():
        marker = cv2.cvtColor(
            aruco.generateImageMarker(dictionary, marker_id, msize), cv2.COLOR_GRAY2BGR
        )
        half = msize // 2
        photo[my - half - pad : my + half + pad, mx - half - pad : mx + half + pad] = 255
        photo[my - half : my + half, mx - half : mx + half] = marker

    # Linear map from canonical (rectified) coordinates back to photo coordinates.
    scale = (n - 2 * inset) / n
    pitch = n * (1 - 2 * spec.margin_frac) / max(spec.rows, spec.cols)
    axes = (int(0.30 * pitch * scale), int(0.21 * pitch * scale))
    for well in occupied:
        cx, cy = well_centres(spec)[well]
        px, py = int(cx * scale + inset), int(cy * scale + inset)
        cv2.ellipse(photo, (px, py), axes, 25, 0, 360, (95, 135, 110), -1)
    return photo


def test_extract_finds_exactly_the_occupied_wells():
    spec = TraySpec(rows=3, cols=4, canvas_px=1500, margin_frac=0.20)
    occupied = {(0, 0), (0, 3), (1, 1), (2, 2)}
    beans = extract_beans(_make_tray(spec, occupied), spec)
    assert set(beans) == occupied
    assert all(crop.size > 0 for crop in beans.values())


def test_rectify_raises_when_markers_missing():
    spec = TraySpec(rows=2, cols=2, canvas_px=800)
    blank = np.full((800, 800, 3), 200, dtype=np.uint8)
    with pytest.raises(TrayError):
        rectify(blank, spec)


def test_pair_sides_matches_flipped_wells():
    spec = TraySpec(rows=2, cols=4, canvas_px=1500, margin_frac=0.20, flip="mirror_cols")
    occupied = {(0, 0), (0, 1), (1, 3)}
    mirrored = {(r, spec.cols - 1 - c) for r, c in occupied}
    beans_a = extract_beans(_make_tray(spec, occupied), spec)
    beans_b = extract_beans(_make_tray(spec, mirrored), spec)
    paired = pair_sides(beans_a, beans_b, spec)
    assert set(paired) == occupied
    assert all(len(views) == 2 for views in paired.values())


def test_pair_sides_keeps_unmatched_wells_single_view():
    spec = TraySpec(rows=2, cols=3, flip="mirror_cols")
    dummy = np.zeros((6, 6, 3), dtype=np.uint8)
    side_a = {(0, 0): dummy, (1, 2): dummy}
    side_b = {(0, 2): dummy}  # mirror_cols(0,0) == (0,2); (1,2) has no partner
    paired = pair_sides(side_a, side_b, spec)
    assert len(paired[(0, 0)]) == 2
    assert len(paired[(1, 2)]) == 1
