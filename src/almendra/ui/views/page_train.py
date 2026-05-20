"""Train page — form + Start/Stop + live Plotly chart tailing the metrics JSONL."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from almendra.ui.components.charts import training_curve
from almendra.ui.components.i18n import Lang, t
from almendra.ui.components.instructions import train_help
from almendra.ui.components.state import get_state, set_state
from almendra.ui.discovery import outputs_root
from almendra.ui.metrics_io import read_live_metrics
from almendra.ui.process import is_running, start_training, stop

_BACKBONES = [
    "mobilenet_v3_small",
    "mobilenet_v3_large",
    "efficientnet_b0",
]
_FUSIONS = ["attention", "gated", "mean", "max"]


def _render_form(lang: Lang) -> dict[str, object]:
    """Render the training-knob form; return a dict of Hydra-style values."""
    col1, col2, col3 = st.columns(3)
    with col1:
        backbone = st.selectbox(t("train.backbone", lang), _BACKBONES, index=0)
        epochs = st.number_input(t("train.epochs", lang), min_value=1, max_value=300, value=30)
    with col2:
        lr = st.select_slider(
            t("train.lr", lang),
            options=[1e-4, 3e-4, 1e-3, 3e-3, 1e-2],
            value=3e-4,
            format_func=lambda v: f"{v:.0e}",
        )
        image_size = st.selectbox(t("train.image_size", lang), [160, 192, 224, 256], index=2)
    with col3:
        batch_size = st.selectbox(t("train.batch_size", lang), [16, 32, 64, 128], index=2)
        pseudo_views = st.checkbox(t("train.pseudo_views", lang), value=False)

    advanced: dict[str, object] = {}
    with st.expander(t("common.advanced", lang), expanded=False):
        fusion = st.selectbox(t("train.fusion", lang), _FUSIONS, index=0)
        view_dropout = st.slider(
            t("train.view_dropout", lang), min_value=0.0, max_value=0.7, value=0.0, step=0.05
        )
        augmentation = st.checkbox(t("train.augmentation", lang), value=True)
        advanced["model.fusion"] = fusion
        advanced["model.view_dropout"] = view_dropout
        if not augmentation:
            advanced["train.augmentation.hflip"] = False
            advanced["train.augmentation.vflip"] = False
            advanced["train.augmentation.color_jitter"] = 0.0

    knobs: dict[str, object] = {
        "model.backbone": backbone,
        "model.name": backbone,
        "train.epochs": int(epochs),
        "train.optimizer.lr": float(lr),
        "data.image_size": int(image_size),
        "train.batch_size": int(batch_size),
        "data.pseudo_views": pseudo_views,
    }
    knobs.update(advanced)
    return knobs


def _overrides_from_knobs(knobs: dict[str, object]) -> list[str]:
    overrides: list[str] = []
    for key, value in knobs.items():
        if isinstance(value, bool):
            overrides.append(f"{key}={'true' if value else 'false'}")
        elif isinstance(value, float):
            overrides.append(f"{key}={value:.6g}")
        else:
            overrides.append(f"{key}={value}")
    return overrides


def _resolve_run_dir() -> Path:
    """A timestamped directory under ``outputs/`` so concurrent runs don't collide."""
    return outputs_root() / f"ui-{time.strftime('%Y%m%d-%H%M%S')}"


def render(lang: Lang) -> None:
    st.title(t("train.title", lang))
    knobs = _render_form(lang)

    pid = int(get_state("almendra.train.pid", 0))
    metrics_path = get_state("almendra.train.metrics_path", "")
    running = bool(pid) and is_running(pid)

    start_col, stop_col, status_col = st.columns([1, 1, 3])
    with start_col:
        start_clicked = st.button(
            t("train.start_btn", lang),
            type="primary",
            disabled=running,
            use_container_width=True,
        )
    with stop_col:
        stop_clicked = st.button(
            t("train.stop_btn", lang),
            disabled=not running,
            use_container_width=True,
        )
    with status_col:
        if running:
            st.info(f"⏳ {t('train.running', lang)} (pid {pid})")
        elif metrics_path:
            st.success(f"✅ {t('train.done', lang)}")

    if start_clicked and not running:
        run_dir = _resolve_run_dir()
        handle = start_training(
            run_dir, overrides=_overrides_from_knobs(knobs), cwd=outputs_root().parent
        )
        set_state("almendra.train.pid", handle.pid)
        set_state("almendra.train.metrics_path", str(handle.metrics_path))
        set_state("almendra.train.output_dir", str(handle.output_dir))
        st.rerun()

    if stop_clicked and running:
        stop(pid)
        set_state("almendra.train.pid", 0)
        st.rerun()

    metrics_path = get_state("almendra.train.metrics_path", "")
    if not metrics_path:
        st.caption(t("common.no_runs", lang))
        return

    snapshot = read_live_metrics(metrics_path)
    if snapshot.epochs_total:
        st.progress(snapshot.progress, text=f"{snapshot.epochs_completed}/{snapshot.epochs_total}")

    if snapshot.val_macro_f1:
        st.metric(
            label=t("train.best_so_far", lang),
            value=f"{max(snapshot.val_macro_f1):.4f}",
        )
        st.subheader(t("train.chart_title", lang))
        st.plotly_chart(
            training_curve(snapshot.epoch, snapshot.train_loss, snapshot.val_macro_f1),
            use_container_width=True,
        )
    with st.expander("ℹ️", expanded=False):
        st.markdown(train_help(lang))

    # Auto-refresh while training is alive — Streamlit reruns the whole script.
    if running and not snapshot.done:
        time.sleep(2.0)
        st.rerun()
