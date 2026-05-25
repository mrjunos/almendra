"""Quantize / Export page — turn a trained checkpoint into ONNX (+ INT8).

Separate from Train on purpose: export and quantization are their own step in
the pipeline (train → evaluate → **quantize** → predict). Runs in-process and
only on an explicit click, like the Evaluate page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from almendra.ui.components.i18n import Lang, t
from almendra.ui.discovery import list_runs

_MODES = ["int8_dynamic", "int8_static", "none"]


def _mb(path: Path) -> float:
    return path.stat().st_size / 1e6


def _run_export(ckpt_path: Path, mode: str) -> dict[str, Any] | None:
    """Compose the Hydra config and export the checkpoint in-process."""
    try:
        import torch
        from hydra import compose, initialize_config_dir
        from hydra.core.global_hydra import GlobalHydra
        from omegaconf import OmegaConf

        from almendra.export import exporter
        from almendra.paths import configs_dir
    except ImportError as exc:
        st.error(f"Missing dependency for export: {exc}")
        return None

    # Reconstruct the model/image-size the checkpoint was trained with so the
    # exporter rebuilds a matching graph (a non-default backbone would otherwise
    # fail to load the state dict).
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model_cfg = ckpt.get("model_cfg") or ckpt.get("config", {}).get("model")
    image_size = ckpt.get("image_size")

    GlobalHydra.instance().clear()
    with initialize_config_dir(version_base=None, config_dir=str(configs_dir())):
        cfg = compose(
            config_name="config",
            overrides=[
                f"output_dir={ckpt_path.parent}",
                f"export.quantize.mode={mode}",
            ],
        )
    if model_cfg:
        cfg.model = OmegaConf.merge(cfg.model, OmegaConf.create(model_cfg))
    if image_size:
        cfg.data.image_size = int(image_size)

    return exporter.run(cfg, checkpoint=str(ckpt_path))


def render(lang: Lang) -> None:
    st.title(t("quantize.title", lang))
    st.caption(t("quantize.help", lang))

    runs = [r for r in list_runs() if r.checkpoint]
    if not runs:
        st.warning(t("quantize.no_checkpoints", lang))
        return

    col_ckpt, col_mode = st.columns([3, 2])
    with col_ckpt:
        names = [r.name for r in runs]
        pick = st.selectbox(t("quantize.checkpoint", lang), names, index=0)
        run = next(r for r in runs if r.name == pick)
    with col_mode:
        mode = st.selectbox(t("quantize.mode", lang), _MODES, index=0)

    if not st.button(t("quantize.run_btn", lang), type="primary", key="quantize.run"):
        return

    with st.spinner("…"):
        result = _run_export(run.checkpoint, mode)
    if not result:
        return

    st.success(t("quantize.parity_ok", lang))

    float_path = Path(result["float_onnx"])
    int8_raw = result.get("int8_onnx")
    int8_path = Path(int8_raw) if int8_raw else None

    c1, c2, c3 = st.columns(3)
    c1.metric(t("quantize.float_model", lang), f"{_mb(float_path):.2f} MB")
    if int8_path is not None and int8_path.is_file():
        reduction = 100.0 * (1.0 - _mb(int8_path) / max(_mb(float_path), 1e-9))
        c2.metric(t("quantize.int8_model", lang), f"{_mb(int8_path):.2f} MB")
        c3.metric(t("quantize.reduction", lang), f"{reduction:.0f}%")
    elif mode != "none":
        c2.warning(t("quantize.int8_skipped", lang))

    st.markdown(f"- `{float_path}`")
    if int8_path is not None and int8_path.is_file():
        st.markdown(f"- `{int8_path}`")
