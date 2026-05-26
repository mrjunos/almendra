"""Evaluate a trained checkpoint on a dataset split.

Reports accuracy, macro-F1, the per-class breakdown, and the missed-defect rate
— the metric that matters most for a sorter (a defect classified as sound).
"""

from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import DataLoader

from almendra.datasets.manifest import filter_split, read_manifest
from almendra.datasets.multiview import MultiViewBeanDataset
from almendra.datasets.transforms import build_transforms
from almendra.eval.metrics import DEFAULT_THRESHOLD, compute_metrics, missed_defect_rate
from almendra.models.classifier import build_model
from almendra.paths import processed_dir
from almendra.taxonomy import get_taxonomy
from almendra.train.loop import resolve_device


def _load_model(ckpt_path: Path, model_cfg, num_classes: int, device):
    model = build_model(model_cfg, num_classes).to(device)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model


@torch.no_grad()
def _predict(model, loader, device, threshold: float = DEFAULT_THRESHOLD):
    """Return (y_true, y_pred) as (N, C) multi-label indicator matrices."""
    preds, targets = [], []
    for views, labels in loader:
        logits = model(views.to(device))
        preds.append((torch.sigmoid(logits) >= threshold).int().cpu())
        targets.append(labels.int())
    return torch.cat(targets).numpy(), torch.cat(preds).numpy()


def _print_report(metrics: dict, mdr: float, taxonomy) -> None:
    print(f"accuracy        {metrics['accuracy']:.4f}")
    print(
        f"macro-F1        {metrics['macro_f1']:.4f}  "
        f"({metrics['n_classes_present']} classes present)"
    )
    print(f"missed-defect   {mdr:.4f}  (true defects predicted as sound)")
    print(f"\n{'class':<22} {'prec':>7} {'recall':>7} {'f1':>7} {'support':>8}")
    for i, name in enumerate(taxonomy.class_names()):
        per_class = metrics["per_class"][i]
        if per_class["support"] == 0:
            continue
        print(
            f"{name:<22} {per_class['precision']:>7.3f} {per_class['recall']:>7.3f} "
            f"{per_class['f1']:>7.3f} {per_class['support']:>8}"
        )


def run(
    cfg,
    checkpoint: str | None = None,
    split: str = "test",
    views: int | None = None,
) -> dict:
    """Evaluate a checkpoint and return the metrics dict.

    `views` overrides the evaluation view count — pass 1/2/4 to probe a
    multi-view checkpoint's view-count robustness (the model is view-agnostic).
    """
    taxonomy = get_taxonomy()
    num_classes = taxonomy.num_defect_classes
    device = resolve_device(cfg.device)
    if views is not None:
        cfg.model.num_views = views

    ckpt_path = Path(checkpoint) if checkpoint else Path(cfg.output_dir) / "best.pt"
    if not ckpt_path.is_file():
        raise FileNotFoundError(f"checkpoint not found: {ckpt_path}")

    model = _load_model(ckpt_path, cfg.model, num_classes, device)
    records = filter_split(read_manifest(processed_dir() / "manifest.jsonl"), split)
    if not records:
        raise RuntimeError(f"no records in split '{split}'")

    transform = build_transforms(cfg.data.image_size, None, train=False)
    loader = DataLoader(
        MultiViewBeanDataset(
            records,
            transform,
            cfg.model.num_views,
            0.0,
            pseudo_views=cfg.data.get("pseudo_views", False),
        ),
        batch_size=cfg.train.batch_size,
        num_workers=cfg.data.num_workers,
    )
    targets, preds = _predict(model, loader, device)

    reject_indices = [c.index for c in taxonomy.defect_classes.values() if not c.accept]
    metrics = compute_metrics(targets, preds, num_classes)
    metrics["missed_defect_rate"] = missed_defect_rate(targets, preds, reject_indices)
    metrics["confusion_matrix"] = None  # not defined for multi-label; per-class table instead

    print(
        f"\n=== evaluation on '{split}' split "
        f"({len(records)} beans, {cfg.model.num_views} view(s)) ==="
    )
    _print_report(metrics, metrics["missed_defect_rate"], taxonomy)
    return metrics
