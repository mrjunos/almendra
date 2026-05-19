"""Auto-segmentation of gridded-tray photos into per-bean crops.

Capture workflow (see ``capture/protocol.md``): beans are laid one-per-well in a
tray with four ArUco markers at its corners; one side is photographed, the tray
is flipped, the other side is photographed. This module turns those photos into
per-bean crops:

1. :func:`rectify` — warp a photo to a canonical top-down frame via the markers.
2. :func:`extract_from_rectified` — crop and tighten each well to a single bean.
3. :func:`pair_sides` — match side-A and side-B wells into two-view beans.

A well's ``(row, col)`` address *is* the bean's identity, so correspondence
across the flip is arithmetic — no per-bean handling, no manual annotation.

Requires the ``capture`` extra (``uv sync --extra capture``) for OpenCV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


class TrayError(RuntimeError):
    """Raised when a tray photo cannot be processed (e.g. markers not found)."""


@dataclass
class TraySpec:
    """Geometry of a gridded capture tray."""

    rows: int
    cols: int
    marker_dict: str = "DICT_4X4_50"
    # ArUco IDs at the corners, ordered: top-left, top-right, bottom-right, bottom-left.
    corner_ids: tuple[int, int, int, int] = (0, 1, 2, 3)
    canvas_px: int = 2000  # side length of the rectified square frame
    margin_frac: float = 0.10  # grid inset from the marker-centre quad
    well_frac: float = 0.85  # well crop window as a fraction of the cell pitch
    flip: str = "mirror_cols"  # side-B -> side-A map: identity | mirror_rows | mirror_cols
    min_bean_area_frac: float = 0.04  # min bean area / window area to count a well occupied
    max_bean_area_frac: float = 0.90  # above this, segmentation is treated as failed/empty


def load_image(path: str | Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise TrayError(f"could not read image: {path}")
    return image


def save_image(image: np.ndarray, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def _detect_marker_centres(image: np.ndarray, spec: TraySpec) -> dict[int, tuple[float, float]]:
    """Return ``{marker_id: (cx, cy)}`` for every ArUco marker found."""
    aruco = cv2.aruco
    dict_id = getattr(aruco, spec.marker_dict, None)
    if dict_id is None:
        raise TrayError(f"unknown ArUco dictionary: {spec.marker_dict}")
    detector = aruco.ArucoDetector(
        aruco.getPredefinedDictionary(dict_id), aruco.DetectorParameters()
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = detector.detectMarkers(gray)
    centres: dict[int, tuple[float, float]] = {}
    if ids is None:
        return centres
    for marker, marker_id in zip(corners, ids.flatten(), strict=True):
        point = marker.reshape(-1, 2).mean(axis=0)
        centres[int(marker_id)] = (float(point[0]), float(point[1]))
    return centres


def rectify(image: np.ndarray, spec: TraySpec) -> np.ndarray:
    """Warp a tray photo to a canonical ``canvas_px`` square via the 4 corner markers."""
    centres = _detect_marker_centres(image, spec)
    missing = [i for i in spec.corner_ids if i not in centres]
    if missing:
        raise TrayError(f"corner markers {missing} not found (detected {sorted(centres)})")
    src = np.array([centres[i] for i in spec.corner_ids], dtype=np.float32)
    size = spec.canvas_px
    dst = np.array([[0, 0], [size, 0], [size, size], [0, size]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image, transform, (size, size))


def _cell_pitch(spec: TraySpec) -> float:
    inner = spec.canvas_px * (1 - 2 * spec.margin_frac)
    return min(inner / spec.cols, inner / spec.rows)


def well_centres(spec: TraySpec) -> dict[tuple[int, int], tuple[float, float]]:
    """Canonical ``(x, y)`` pixel of each well centre, keyed by ``(row, col)``."""
    margin = spec.margin_frac * spec.canvas_px
    inner = spec.canvas_px - 2 * margin
    centres = {}
    for row in range(spec.rows):
        for col in range(spec.cols):
            x = margin + inner * (col + 0.5) / spec.cols
            y = margin + inner * (row + 0.5) / spec.rows
            centres[(row, col)] = (x, y)
    return centres


def _segment_window(window: np.ndarray, spec: TraySpec) -> np.ndarray | None:
    """Find the central bean in a well window; return a tight crop, or None if empty."""
    height, width = window.shape[:2]
    if height < 8 or width < 8:
        return None

    # Estimate the background (tray) colour from a thin border ring of the window.
    ring = np.concatenate(
        [
            window[:3].reshape(-1, 3),
            window[-3:].reshape(-1, 3),
            window[:, :3].reshape(-1, 3),
            window[:, -3:].reshape(-1, 3),
        ]
    )
    background = np.median(ring, axis=0)
    distance = np.linalg.norm(window.astype(np.float32) - background, axis=2)
    distance8 = np.clip(distance, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(distance8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    centre = (width / 2, height / 2)

    def offset_from_centre(contour) -> float:
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            return 1e9
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        return float(np.hypot(cx - centre[0], cy - centre[1]))

    contour = min(contours, key=offset_from_centre)
    area = cv2.contourArea(contour)
    window_area = height * width
    if not spec.min_bean_area_frac * window_area <= area <= spec.max_bean_area_frac * window_area:
        return None

    x, y, box_w, box_h = cv2.boundingRect(contour)
    pad = int(0.12 * max(box_w, box_h))
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(width, x + box_w + pad), min(height, y + box_h + pad)
    return window[y0:y1, x0:x1].copy()


def _window(rectified: np.ndarray, centre: tuple[float, float], half: int) -> np.ndarray:
    x, y = int(round(centre[0])), int(round(centre[1]))
    return rectified[max(0, y - half) : y + half, max(0, x - half) : x + half]


def extract_from_rectified(
    rectified: np.ndarray, spec: TraySpec
) -> dict[tuple[int, int], np.ndarray]:
    """Crop every occupied well of an already-rectified tray image."""
    half = int(spec.well_frac * _cell_pitch(spec) / 2)
    beans: dict[tuple[int, int], np.ndarray] = {}
    for well, centre in well_centres(spec).items():
        window = _window(rectified, centre, half)
        if window.size == 0:
            continue
        crop = _segment_window(window, spec)
        if crop is not None and crop.size > 0:
            beans[well] = crop
    return beans


def extract_beans(image: np.ndarray, spec: TraySpec) -> dict[tuple[int, int], np.ndarray]:
    """Rectify a tray photo and crop every occupied well."""
    return extract_from_rectified(rectify(image, spec), spec)


def _flip_well(row: int, col: int, spec: TraySpec) -> tuple[int, int]:
    if spec.flip == "identity":
        return (row, col)
    if spec.flip == "mirror_cols":
        return (row, spec.cols - 1 - col)
    if spec.flip == "mirror_rows":
        return (spec.rows - 1 - row, col)
    raise TrayError(f"unknown flip mode: {spec.flip}")


def pair_sides(
    side_a: dict[tuple[int, int], np.ndarray],
    side_b: dict[tuple[int, int], np.ndarray],
    spec: TraySpec,
) -> dict[tuple[int, int], list[np.ndarray]]:
    """Pair side-A and side-B wells into per-bean view lists, keyed by the side-A well."""
    paired: dict[tuple[int, int], list[np.ndarray]] = {}
    for well, crop_a in side_a.items():
        crop_b = side_b.get(_flip_well(well[0], well[1], spec))
        paired[well] = [crop_a] if crop_b is None else [crop_a, crop_b]
    return paired


def draw_overlay(rectified: np.ndarray, spec: TraySpec, occupied=None) -> np.ndarray:
    """Annotate a rectified image with the well grid; occupied wells in green."""
    overlay = rectified.copy()
    occupied = set(occupied or [])
    half = int(spec.well_frac * _cell_pitch(spec) / 2)
    for well, centre in well_centres(spec).items():
        x, y = int(round(centre[0])), int(round(centre[1]))
        colour = (0, 200, 0) if well in occupied else (0, 0, 200)
        cv2.rectangle(overlay, (x - half, y - half), (x + half, y + half), colour, 3)
        cv2.putText(
            overlay,
            f"{well[0]},{well[1]}",
            (x - half + 6, y - half + 34),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            colour,
            2,
        )
    return overlay
