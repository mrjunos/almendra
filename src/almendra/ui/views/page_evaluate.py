"""Evaluate page — checkpoint picker, metrics, confusion matrix, error gallery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from almendra.ui.components.charts import confusion_heatmap
from almendra.ui.components.i18n import Lang, t
from almendra.ui.discovery import list_runs, project_root


def _run_evaluation(ckpt_path: Path, split: str) -> dict[str, Any] | None:
    """Run evaluation in-process. Heavy: only triggered on explicit click."""
    try:
        from hydra import compose, initialize_config_dir
        from hydra.core.global_hydra import GlobalHydra

        from almendra.eval import evaluate as eval_module
        from almendra.paths import configs_dir
    except ImportError as exc:
        st.error(f"Missing dependency for evaluation: {exc}")
        return None

    GlobalHydra.instance().clear()
    with initialize_config_dir(version_base=None, config_dir=str(configs_dir())):
        cfg = compose(
            config_name="config",
            overrides=[f"output_dir={ckpt_path.parent}"],
        )
    return eval_module.run(cfg, checkpoint=str(ckpt_path), split=split)


def _collect_misclassified(
    ckpt_path: Path, split: str, max_items: int = 24
) -> list[dict[str, Any]]:
    """Return up to ``max_items`` mis-classified bean records for the gallery."""
    try:
        import torch
        from torch.utils.data import DataLoader

        from almendra.datasets.manifest import filter_split, read_manifest
        from almendra.datasets.multiview import MultiViewBeanDataset
        from almendra.datasets.transforms import build_transforms
        from almendra.models.classifier import build_model
        from almendra.paths import processed_dir
        from almendra.taxonomy import get_taxonomy
        from almendra.train.loop import resolve_device
    except ImportError:
        return []

    taxonomy = get_taxonomy()
    device = resolve_device("auto")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model_cfg = ckpt.get("config", {}).get("model", {})
    image_size = int(ckpt.get("image_size", 224))
    num_views = int(model_cfg.get("num_views", 1))

    from types import SimpleNamespace

    cfg_obj = (
        SimpleNamespace(**model_cfg)
        if model_cfg
        else SimpleNamespace(
            backbone="mobilenet_v3_small",
            pretrained=False,
            embedding_dim=576,
            dropout=0.2,
            num_views=1,
            fusion="attention",
            view_dropout=0.0,
        )
    )
    model = build_model(cfg_obj, taxonomy.num_defect_classes).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()

    records = filter_split(read_manifest(processed_dir() / "manifest.jsonl"), split)
    if not records:
        return []
    transform = build_transforms(image_size, None, train=False)
    dataset = MultiViewBeanDataset(records, transform, num_views, 0.0)
    loader = DataLoader(dataset, batch_size=32, shuffle=False)

    errors: list[dict[str, Any]] = []
    class_names = taxonomy.class_names()
    record_iter = iter(records)

    def _names(indices) -> str:
        return "+".join(class_names[i] for i in indices) or "—"

    with torch.no_grad():
        for views, labels in loader:
            # Multi-label: a bean is "wrong" when its predicted defect set differs
            # from the true set (thresholded sigmoid).
            pred_mat = (torch.sigmoid(model(views.to(device))) >= 0.5).int().cpu().numpy()
            true_mat = labels.int().cpu().numpy()
            for pred_row, true_row in zip(pred_mat, true_mat, strict=True):
                rec = next(record_iter)
                pred_idx = [i for i, v in enumerate(pred_row) if v]
                true_idx = [i for i, v in enumerate(true_row) if v]
                if pred_idx != true_idx and len(errors) < max_items:
                    image_path = Path(rec.views[0])
                    if not image_path.is_absolute():
                        image_path = processed_dir() / image_path
                    errors.append(
                        {
                            "bean_id": rec.bean_id,
                            "image": image_path,
                            "true": _names(true_idx),
                            "pred": _names(pred_idx),
                        }
                    )
            if len(errors) >= max_items:
                break
    return errors


def render(lang: Lang) -> None:
    st.title(t("evaluate.title", lang))
    runs = [r for r in list_runs() if r.checkpoint]
    if not runs:
        st.warning(t("evaluate.no_checkpoints", lang))
        return

    col_ckpt, col_split = st.columns([3, 1])
    with col_ckpt:
        names = [r.name for r in runs]
        pick = st.selectbox(t("evaluate.checkpoint", lang), names, index=0)
        run = next(r for r in runs if r.name == pick)
    with col_split:
        split = st.selectbox(t("evaluate.split", lang), ["test", "val", "train"], index=0)

    if not st.button(t("common.run", lang), type="primary"):
        return

    with st.spinner("…"):
        metrics = _run_evaluation(run.checkpoint, split)
    if not metrics:
        return

    m1, m2, m3 = st.columns(3)
    m1.metric(t("evaluate.headline_acc", lang), f"{metrics['accuracy']:.3f}")
    m2.metric(t("evaluate.headline_f1", lang), f"{metrics['macro_f1']:.3f}")
    m3.metric(t("evaluate.headline_mdr", lang), f"{metrics.get('missed_defect_rate', 0.0):.3f}")

    try:
        from almendra.taxonomy import get_taxonomy

        taxonomy = get_taxonomy()
        class_names = taxonomy.class_names()
    except Exception:
        class_names = [str(i) for i in range(len(metrics.get("per_class", {})))]

    st.subheader(t("evaluate.per_class", lang))
    per_class = metrics.get("per_class", {})
    rows = [
        {
            "class": class_names[i] if i < len(class_names) else str(i),
            "precision": v["precision"],
            "recall": v["recall"],
            "f1": v["f1"],
            "support": v["support"],
        }
        for i, v in per_class.items()
        if v["support"] > 0
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)

    cm = metrics.get("confusion_matrix")
    if cm:
        st.subheader(t("evaluate.confusion", lang))
        st.plotly_chart(
            confusion_heatmap(cm, class_names[: len(cm)]),
            use_container_width=True,
        )

    st.subheader(t("evaluate.gallery", lang))
    try:
        errors = _collect_misclassified(run.checkpoint, split)
    except Exception as exc:
        st.caption(f"gallery unavailable: {exc}")
        errors = []
    if not errors:
        st.caption("—")
    else:
        cols = st.columns(4)
        for i, err in enumerate(errors):
            col = cols[i % 4]
            try:
                col.image(
                    str(err["image"]),
                    caption=t("evaluate.gallery_caption", lang, pred=err["pred"], true=err["true"]),
                    use_container_width=True,
                )
            except Exception:
                col.caption(f"({err['bean_id']}) {err['pred']} ⟵ {err['true']}")


# Make project_root importable in tests/etc.
__all__ = ["render", "project_root"]
