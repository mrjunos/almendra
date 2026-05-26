"""Predict page — upload one bean photo and run the latest ONNX model on it.

Has two modes: a single model, or a side-by-side comparison of a run's float
ONNX against its INT8 ONNX (same image, two sessions) so the accuracy/size
trade-off of quantization is visible at a glance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

from almendra.ui.components.i18n import Lang, t
from almendra.ui.discovery import best_onnx_for_prediction, list_runs

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _preprocess(image: Image.Image, size: int) -> np.ndarray:
    """Resize, normalise, and shape into the multi-view tensor the model expects."""
    rgb = image.convert("RGB").resize((size, size))
    array = np.asarray(rgb, dtype=np.float32) / 255.0
    array = (array - _IMAGENET_MEAN) / _IMAGENET_STD
    chw = np.transpose(array, (2, 0, 1))
    # Model input shape: (batch=1, views=1, C, H, W).
    return chw[None, None].astype(np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    exp = np.exp(logits - logits.max(axis=-1, keepdims=True))
    return exp / exp.sum(axis=-1, keepdims=True)


@dataclass
class _Inference:
    probs: np.ndarray
    top_idx: int
    latency_ms: float


def _infer(onnx_path: Path, image: Image.Image) -> _Inference:
    """Run one ONNX model on the image; return probabilities + latency."""
    import onnxruntime as ort  # type: ignore

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    input_shape = session.get_inputs()[0].shape
    # The model's H/W dims may be symbolic; use the run-time fallback of 224.
    spatial = [d for d in input_shape if isinstance(d, int) and d > 1]
    image_size = int(spatial[-1]) if spatial else 224

    tensor = _preprocess(image, image_size)
    t0 = time.perf_counter()
    logits = session.run(None, {input_name: tensor})[0][0]
    latency_ms = (time.perf_counter() - t0) * 1000.0
    return _Inference(_softmax(logits), int(np.argmax(logits)), latency_ms)


def _render_result(
    container, title: str, result: _Inference, class_names, taxonomy, lang: Lang
) -> None:
    """Render one model's prediction (class, confidence, verdict, top-3, latency)."""
    probs, top_idx = result.probs, result.top_idx
    top_name = class_names[top_idx] if top_idx < len(class_names) else str(top_idx)
    container.subheader(title)
    container.metric(t("predict.predicted", lang), top_name)
    container.metric(t("predict.confidence", lang), f"{probs[top_idx]:.1%}")
    container.caption(f"{t('predict.latency', lang)}: {result.latency_ms:.1f} ms")
    if taxonomy is not None:
        accept = taxonomy.is_accept(top_name)
        verdict_key = "predict.verdict_accept" if accept else "predict.verdict_reject"
        container.markdown(f"### {t(verdict_key, lang)}")

    order = np.argsort(probs)[::-1][:3]
    rows = [
        {
            "rank": rank + 1,
            "class": class_names[i] if i < len(class_names) else str(i),
            "probability": float(probs[i]),
        }
        for rank, i in enumerate(order)
    ]
    container.dataframe(rows, hide_index=True, use_container_width=True)


def render(lang: Lang) -> None:
    st.title(t("predict.title", lang))

    runs = list_runs()
    candidates: list[Path] = []
    for r in runs:
        if r.onnx_int8:
            candidates.append(r.onnx_int8)
        if r.onnx_float:
            candidates.append(r.onnx_float)
    default = best_onnx_for_prediction()
    if not candidates or default is None:
        st.warning(t("predict.no_model", lang))
        return

    compare = st.checkbox(t("predict.compare", lang), key="predict.compare")

    default_idx = candidates.index(default) if default in candidates else 0
    pick = st.selectbox(
        "ONNX",
        candidates,
        index=default_idx,
        format_func=lambda p: f"{p.parent.name}/{p.name}",
        disabled=compare,
    )

    uploaded = st.file_uploader(
        t("predict.upload", lang), type=["jpg", "jpeg", "png"], key="predict.upload"
    )
    if uploaded is None:
        return

    try:
        import onnxruntime  # type: ignore  # noqa: F401
    except ImportError:
        st.error("onnxruntime is not installed. `uv sync --extra export`.")
        return

    image = Image.open(uploaded)
    st.image(image, width=256)

    try:
        from almendra.taxonomy import get_taxonomy

        taxonomy = get_taxonomy()
        class_names = taxonomy.class_names()
    except Exception:
        taxonomy = None
        class_names = []

    if compare:
        both = [r for r in runs if r.onnx_float and r.onnx_int8]
        if not both:
            st.warning(t("predict.compare_unavailable", lang))
            return
        # Prefer the run that owns the picked model; else the most recent qualifying run.
        run = next((r for r in both if pick in (r.onnx_float, r.onnx_int8)), both[0])
        st.caption(f"`{run.name}`")
        col_f, col_i = st.columns(2)
        res_f = _infer(run.onnx_float, image)
        res_i = _infer(run.onnx_int8, image)
        _render_result(col_f, t("predict.model_float", lang), res_f, class_names, taxonomy, lang)
        _render_result(col_i, t("predict.model_int8", lang), res_i, class_names, taxonomy, lang)
        agree = res_f.top_idx == res_i.top_idx
        st.metric(
            t("predict.agreement", lang),
            t("predict.agreement_yes" if agree else "predict.agreement_no", lang),
        )
        return

    result = _infer(pick, image)
    top_idx = result.top_idx
    top_name = class_names[top_idx] if top_idx < len(class_names) else str(top_idx)
    headline_col, verdict_col = st.columns([2, 1])
    headline_col.metric(t("predict.predicted", lang), top_name)
    headline_col.metric(t("predict.confidence", lang), f"{result.probs[result.top_idx]:.1%}")
    if taxonomy is not None:
        accept = taxonomy.is_accept(top_name)
        verdict_key = "predict.verdict_accept" if accept else "predict.verdict_reject"
        verdict_col.markdown(f"### {t(verdict_key, lang)}")

    st.subheader(t("predict.top3", lang))
    order = np.argsort(result.probs)[::-1][:3]
    rows = [
        {
            "rank": rank + 1,
            "class": class_names[i] if i < len(class_names) else str(i),
            "probability": float(result.probs[i]),
        }
        for rank, i in enumerate(order)
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)
