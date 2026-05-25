"""Tray Capture page — upload tray photos, preview rectified+overlay, save crops.

Calls into ``almendra.datasets.tray`` (which needs the ``capture`` extra). If
OpenCV is not installed, we degrade gracefully with a clear error.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

from almendra.ui.components.i18n import Lang, t
from almendra.ui.components.instructions import tray_help
from almendra.ui.discovery import project_root

_FLIP_MODES = ["identity", "mirror_rows", "mirror_cols"]
_MARKER_DICTS = [
    "DICT_4X4_50",
    "DICT_5X5_50",
    "DICT_6X6_50",
    "DICT_ARUCO_ORIGINAL",
]


def _read_uploaded_image(uploaded) -> np.ndarray | None:
    if uploaded is None:
        return None
    import cv2

    raw = np.frombuffer(uploaded.read(), dtype=np.uint8)
    return cv2.imdecode(raw, cv2.IMREAD_COLOR)


def _bgr_to_rgb(image: np.ndarray) -> Image.Image:
    return Image.fromarray(image[:, :, ::-1])


def _save_session(
    paired: dict[tuple[int, int], list[np.ndarray]],
    session_id: str,
    spec_dict: dict,
) -> Path:
    import cv2

    out_dir = project_root() / "data" / "raw" / "proprietary_tray" / "sessions" / session_id
    crops_dir = out_dir / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    saved: list[dict] = []
    for (row, col), views in paired.items():
        for i, crop in enumerate(views):
            name = f"bean_r{row}c{col}_v{i}.png"
            cv2.imwrite(str(crops_dir / name), crop)
            saved.append({"row": row, "col": col, "view": i, "file": f"crops/{name}"})

    (out_dir / "session.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "created_at": time.time(),
                "tray_spec": spec_dict,
                "beans": saved,
            },
            indent=2,
        )
    )
    return out_dir


_RESULT_KEY = "almendra.tray.result"


def _process(side_a_file, side_b_file, spec, lang: Lang) -> None:
    """Segment the uploaded photo(s) and stash the result in session_state.

    Persisting here (rather than rendering inline behind the transient Process
    button) is what lets the Save-crops button survive the next rerun — clicking
    Save reruns the script with Process *unclicked*, so anything gated on the
    Process click would vanish before the save could run.
    """
    from almendra.datasets import tray

    st.session_state.pop(_RESULT_KEY, None)
    if side_a_file is None:
        st.warning(f"{t('tray.side_a', lang)} — {t('common.required', lang)}")
        return

    side_a_img = _read_uploaded_image(side_a_file)
    try:
        rect_a = tray.rectify(side_a_img, spec)
    except tray.TrayError:
        st.error(t("tray.error_markers", lang))
        return
    beans_a = tray.extract_from_rectified(rect_a, spec)
    overlay_a = tray.draw_overlay(rect_a, spec, beans_a)

    total = spec.rows * spec.cols
    result: dict = {
        "orig_a": np.asarray(_bgr_to_rgb(side_a_img)),
        "overlay_a": np.asarray(_bgr_to_rgb(overlay_a)),
        "n_a": len(beans_a),
        "total": total,
        "default_id": time.strftime("%Y%m%d-%H%M%S"),
        "spec_dict": {
            "rows": spec.rows,
            "cols": spec.cols,
            "flip": spec.flip,
            "marker_dict": spec.marker_dict,
            "margin_frac": spec.margin_frac,
            "well_frac": spec.well_frac,
        },
    }
    paired: dict[tuple[int, int], list[np.ndarray]] = {
        well: [crop] for well, crop in beans_a.items()
    }

    side_b_img = _read_uploaded_image(side_b_file) if side_b_file is not None else None
    if side_b_img is not None:
        try:
            rect_b = tray.rectify(side_b_img, spec)
        except tray.TrayError:
            st.error(t("tray.error_markers", lang))
            return
        beans_b = tray.extract_from_rectified(rect_b, spec)
        result["orig_b"] = np.asarray(_bgr_to_rgb(side_b_img))
        result["overlay_b"] = np.asarray(_bgr_to_rgb(tray.draw_overlay(rect_b, spec, beans_b)))
        result["n_b"] = len(beans_b)
        paired = tray.pair_sides(beans_a, beans_b, spec)
        two_view = sum(1 for views in paired.values() if len(views) == 2)
        result["two_view"] = two_view
        result["single_view"] = len(paired) - two_view

    result["paired"] = paired
    st.session_state[_RESULT_KEY] = result


def render(lang: Lang) -> None:
    st.title(t("tray.title", lang))
    st.info(t("tray.help_banner", lang))
    with st.expander("ℹ️", expanded=False):
        st.markdown(tray_help(lang))

    try:
        import cv2  # noqa: F401

        from almendra.datasets import tray
    except ImportError:
        st.error(
            "OpenCV is not installed. Run `uv sync --extra capture` (or "
            "`pip install almendra[capture]`) and reload."
        )
        return

    col_uploads, col_spec = st.columns([2, 1])
    with col_uploads:
        side_a_file = st.file_uploader(
            t("tray.side_a", lang),
            type=["jpg", "jpeg", "png"],
            key="tray.side_a",
        )
        side_b_file = st.file_uploader(
            t("tray.side_b", lang),
            type=["jpg", "jpeg", "png"],
            key="tray.side_b",
        )

    with col_spec:
        rows = st.number_input(t("tray.rows", lang), min_value=1, max_value=20, value=6)
        cols = st.number_input(t("tray.cols", lang), min_value=1, max_value=20, value=8)
        flip = st.selectbox(t("tray.flip", lang), _FLIP_MODES, index=2)
        marker_dict = st.selectbox(t("tray.marker_dict", lang), _MARKER_DICTS, index=0)
        margin_frac = st.slider(
            t("tray.margin_frac", lang), min_value=0.0, max_value=0.5, value=0.10, step=0.01
        )
        well_frac = st.slider(
            t("tray.well_frac", lang), min_value=0.5, max_value=1.0, value=0.85, step=0.01
        )

    if st.button(t("tray.process", lang), type="primary", use_container_width=True):
        spec = tray.TraySpec(
            rows=int(rows),
            cols=int(cols),
            flip=flip,
            marker_dict=marker_dict,
            margin_frac=float(margin_frac),
            well_frac=float(well_frac),
        )
        _process(side_a_file, side_b_file, spec, lang)

    result = st.session_state.get(_RESULT_KEY)
    if not result:
        return

    st.subheader("A")
    a_orig, a_rect = st.columns(2)
    a_orig.image(result["orig_a"], caption=t("tray.original", lang))
    a_rect.image(result["overlay_a"], caption=t("tray.rectified", lang))
    st.caption(t("tray.beans_found", lang, n=result["n_a"], total=result["total"]))

    if "overlay_b" in result:
        st.subheader("B")
        b_orig, b_rect = st.columns(2)
        b_orig.image(result["orig_b"], caption=t("tray.original", lang))
        b_rect.image(result["overlay_b"], caption=t("tray.rectified", lang))
        st.caption(t("tray.beans_found", lang, n=result["n_b"], total=result["total"]))
        st.success(
            t("tray.paired_summary", lang, two=result["two_view"], one=result["single_view"])
        )

    st.markdown("---")
    session_id = st.text_input(t("tray.session_id", lang), value=result["default_id"])
    if st.button(t("tray.save_crops", lang), type="primary"):
        out_dir = _save_session(result["paired"], session_id, result["spec_dict"])
        st.success(f"{t('tray.saved_to', lang)}: `{out_dir}`")
