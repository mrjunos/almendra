"""Render a synthetic gridded-tray photo for the E2E test.

There are no real tray photos yet (Phase 3 capture is not collected), but the
crop function (``almendra.datasets.tray``) only needs a photo with four ArUco
corner markers and bean-like blobs in the wells. We composite *real* bean crops
into the wells over a contrasting background so the segmenter finds one bean per
occupied well — exercising the real crop path on realistic imagery.

Geometry mirrors ``tests/test_tray.py:_make_tray`` (the proven generator).
"""

from __future__ import annotations

import cv2
import numpy as np

from almendra.datasets.tray import TraySpec, well_centres

_BG = (180, 70, 200)  # magenta tray background (BGR) — far from any bean colour
_INSET = 200
_MARKER_PX = 160
_MARKER_PAD = 50


def _place_markers(photo: np.ndarray, spec: TraySpec) -> None:
    n = photo.shape[0]
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(getattr(aruco, spec.marker_dict))
    corners = {
        spec.corner_ids[0]: (_INSET, _INSET),
        spec.corner_ids[1]: (n - _INSET, _INSET),
        spec.corner_ids[2]: (n - _INSET, n - _INSET),
        spec.corner_ids[3]: (_INSET, n - _INSET),
    }
    for marker_id, (mx, my) in corners.items():
        marker = cv2.cvtColor(
            aruco.generateImageMarker(dictionary, marker_id, _MARKER_PX), cv2.COLOR_GRAY2BGR
        )
        half = _MARKER_PX // 2
        photo[
            my - half - _MARKER_PAD : my + half + _MARKER_PAD,
            mx - half - _MARKER_PAD : mx + half + _MARKER_PAD,
        ] = 255
        photo[my - half : my + half, mx - half : mx + half] = marker


def make_tray(spec: TraySpec, crops: dict[tuple[int, int], np.ndarray]) -> np.ndarray:
    """Render a tray photo with markers + the given BGR crops pasted into wells."""
    n = spec.canvas_px
    photo = np.full((n, n, 3), _BG, dtype=np.uint8)
    _place_markers(photo, spec)

    # Canonical -> photo coordinate map (markers are inset by _INSET).
    scale = (n - 2 * _INSET) / n
    pitch = n * (1 - 2 * spec.margin_frac) / max(spec.rows, spec.cols)
    target = int(0.5 * pitch * scale)  # pasted crop side in photo pixels

    centres = well_centres(spec)
    for well, crop in crops.items():
        cx, cy = centres[well]
        px, py = int(cx * scale + _INSET), int(cy * scale + _INSET)
        thumb = cv2.resize(crop, (target, target))
        half = target // 2
        photo[py - half : py - half + target, px - half : px - half + target] = thumb
    return photo
