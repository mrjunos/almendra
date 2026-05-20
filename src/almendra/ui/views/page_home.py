"""Home / Status page — dataset stats, recent runs, health, inline wizard."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from almendra.ui.components.i18n import Lang, t
from almendra.ui.discovery import list_runs, manifest_path


def _dataset_stats() -> tuple[int, dict[str, int]]:
    path = manifest_path()
    if not path.is_file():
        return 0, {}
    try:
        from almendra.datasets.manifest import class_distribution, read_manifest

        records = read_manifest(path)
        return len(records), class_distribution(records)
    except Exception:
        return 0, {}


def _torch_version() -> str:
    try:
        import torch

        return torch.__version__
    except ImportError:
        return t("common.not_found")


def _taxonomy_status() -> str:
    try:
        from almendra.taxonomy import get_taxonomy

        tax = get_taxonomy()
        return f"v{tax.schema_version} ({tax.num_defect_classes})"
    except Exception:
        return t("common.not_found")


def render(lang: Lang) -> None:
    st.title(t("home.title", lang))
    st.caption(t("app.tagline", lang))

    left, right = st.columns([2, 1])

    with left:
        st.subheader(t("home.dataset_stats", lang))
        total, dist = _dataset_stats()
        if total == 0:
            st.info(t("home.no_manifest", lang))
        else:
            st.metric(label="beans", value=total)
            if dist:
                rows = sorted(dist.items(), key=lambda kv: kv[1], reverse=True)
                st.dataframe(
                    {"class": [k for k, _ in rows], "count": [v for _, v in rows]},
                    hide_index=True,
                    use_container_width=True,
                )

        st.subheader(t("home.recent_runs", lang))
        runs = list_runs()
        if not runs:
            st.caption(t("common.no_runs", lang))
        else:
            st.dataframe(
                {
                    "run": [r.name for r in runs],
                    "checkpoint": [bool(r.checkpoint) for r in runs],
                    "onnx float": [bool(r.onnx_float) for r in runs],
                    "onnx int8": [bool(r.onnx_int8) for r in runs],
                    "metrics": [bool(r.metrics) for r in runs],
                },
                hide_index=True,
                use_container_width=True,
            )

    with right:
        st.subheader(t("home.health", lang))
        st.markdown(
            f"- **{t('home.health_python', lang)}**: "
            f"{sys.version_info.major}.{sys.version_info.minor}\n"
            f"- **{t('home.health_torch', lang)}**: {_torch_version()}\n"
            f"- **{t('home.health_taxonomy', lang)}**: {_taxonomy_status()}\n"
            f"- **{t('home.health_manifest', lang)}**: "
            f"{'✅' if manifest_path().is_file() else '❌'}"
        )
        st.caption(f"`{Path.cwd()}`")

    st.markdown("---")
    # Wizard buttons jump to other pages. We use an ``on_click`` callback (not
    # ``if st.button(...): ...``) because callbacks fire *before* the next
    # rerun starts — that means the sidebar's render_sidebar can see the new
    # navigation target on the very next render and update the radio's index.
    with st.expander(t("home.wizard_header", lang), expanded=(total == 0)):
        st.markdown(t("home.wizard_intro", lang))
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**{t('home.wizard_step1', lang)}**")
            st.button(
                t("nav.tray", lang),
                key="wizard_tray",
                on_click=_request_nav,
                args=("tray",),
                use_container_width=True,
            )
        with col2:
            st.markdown(f"**{t('home.wizard_step2', lang)}**")
            st.button(
                t("nav.train", lang),
                key="wizard_train",
                on_click=_request_nav,
                args=("train",),
                use_container_width=True,
            )
        with col3:
            st.markdown(f"**{t('home.wizard_step3', lang)}**")
            st.button(
                t("nav.evaluate", lang),
                key="wizard_eval",
                on_click=_request_nav,
                args=("evaluate",),
                use_container_width=True,
            )


def _request_nav(target: str) -> None:
    """Streamlit on_click callback: ask the sidebar to switch pages."""
    import streamlit as st

    st.session_state["almendra.pending_page"] = target
