"""Training loop — Hydra-driven, seeded, MLflow-logged.

Trains the multi-view defect classifier with a class-weighted loss (defects are
rare and imbalanced), a cosine schedule with linear warmup, and early stopping
on validation macro-F1. The best checkpoint is saved and logged to MLflow.
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

import mlflow
import numpy as np
import torch
from omegaconf import OmegaConf
from torch import nn
from torch.utils.data import DataLoader

from almendra.datasets.manifest import filter_split, read_manifest
from almendra.datasets.multiview import MultiViewBeanDataset
from almendra.datasets.transforms import build_transforms
from almendra.eval.metrics import DEFAULT_THRESHOLD, compute_metrics
from almendra.models.classifier import build_model
from almendra.paths import processed_dir
from almendra.taxonomy import get_taxonomy


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _live_metrics_path(output_dir: Path) -> Path | None:
    """Where the UI tails live metrics from. ``ALMENDRA_LIVE_METRICS`` overrides."""
    override = os.environ.get("ALMENDRA_LIVE_METRICS")
    if override:
        return Path(override)
    return output_dir / "live_metrics.jsonl"


def _write_live_metric(path: Path | None, payload: dict) -> None:
    """Append one JSONL line; the Streamlit UI tails this file. Silent on failure."""
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")
    except OSError:
        pass


def resolve_device(name: str) -> torch.device:
    """Resolve 'auto' to cuda > mps > cpu, or honour an explicit device name."""
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def pos_weights(records, num_classes: int, max_weight: float = 100.0) -> torch.Tensor:
    """Per-class positive weights for BCE — counter the defect class imbalance.

    ``pos_weight[c] = n_negative / n_positive`` (clamped), the standard
    ``BCEWithLogitsLoss`` knob that up-weights the rare positive class. Multi-hot
    counting: a bean contributes a positive to every defect it carries. Absent
    classes never occur as positives, so their weight is harmless.
    """
    counts = torch.zeros(num_classes)
    total = 0
    for rec in records:
        total += 1
        for idx in rec.defects or [rec.defect_index]:
            if 0 <= idx < num_classes:
                counts[idx] += 1
    pos = counts.clamp(min=1.0)
    neg = (total - counts).clamp(min=0.0)
    return (neg / pos).clamp(max=max_weight)


def _build_scheduler(optimizer, cfg, epochs: int):
    warmup = cfg.train.scheduler.get("warmup_epochs", 0)
    if warmup > 0 and epochs > warmup:
        warmup_sched = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=0.1, total_iters=warmup
        )
        cosine = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs - warmup)
        return torch.optim.lr_scheduler.SequentialLR(
            optimizer, [warmup_sched, cosine], milestones=[warmup]
        )
    return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)


def _build_loaders(cfg):
    manifest_path = processed_dir() / "manifest.jsonl"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"{manifest_path} not found — run `almendra ingest` first.")
    records = read_manifest(manifest_path)
    train_recs = filter_split(records, "train")
    val_recs = filter_split(records, "val")
    if not train_recs or not val_recs:
        raise RuntimeError("manifest has no train/val records")

    train_tf = build_transforms(cfg.data.image_size, cfg.train.augmentation, train=True)
    eval_tf = build_transforms(cfg.data.image_size, None, train=False)
    num_views = cfg.model.num_views

    pseudo = cfg.data.get("pseudo_views", False)
    train_ds = MultiViewBeanDataset(
        train_recs, train_tf, num_views, cfg.model.view_dropout, pseudo_views=pseudo
    )
    val_ds = MultiViewBeanDataset(val_recs, eval_tf, num_views, 0.0, pseudo_views=pseudo)

    workers = cfg.data.num_workers
    train_dl = DataLoader(
        train_ds, batch_size=cfg.train.batch_size, shuffle=True, num_workers=workers
    )
    val_dl = DataLoader(val_ds, batch_size=cfg.train.batch_size, num_workers=workers)
    return train_dl, val_dl, train_recs


def _train_epoch(model, loader, criterion, optimizer, device) -> float:
    model.train()
    total, seen = 0.0, 0
    for views, labels in loader:
        views, labels = views.to(device), labels.to(device)
        optimizer.zero_grad()
        loss = criterion(model(views), labels)
        loss.backward()
        optimizer.step()
        total += loss.item() * labels.size(0)
        seen += labels.size(0)
    return total / max(seen, 1)


@torch.no_grad()
def _validate(model, loader, device, num_classes: int) -> dict:
    model.eval()
    preds, targets = [], []
    for views, labels in loader:
        logits = model(views.to(device))
        preds.append((torch.sigmoid(logits) >= DEFAULT_THRESHOLD).int().cpu())
        targets.append(labels.int())
    return compute_metrics(torch.cat(targets).numpy(), torch.cat(preds).numpy(), num_classes)


def run(cfg) -> Path:
    """Train a model and return the path of the best checkpoint."""
    taxonomy = get_taxonomy()
    num_classes = taxonomy.num_defect_classes
    set_seed(cfg.seed)
    device = resolve_device(cfg.device)
    print(f"device: {device}")

    train_dl, val_dl, train_recs = _build_loaders(cfg)
    model = build_model(cfg.model, num_classes).to(device)

    # Multi-label: independent per-class sigmoids + BCE, positive-weighted to
    # counter defect imbalance (a bean may carry several defects).
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weights(train_recs, num_classes).to(device))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.train.optimizer.lr,
        weight_decay=cfg.train.optimizer.weight_decay,
    )
    epochs = cfg.train.epochs
    scheduler = _build_scheduler(optimizer, cfg, epochs)

    output_dir = Path(cfg.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = output_dir / "best.pt"

    mlflow.set_tracking_uri(cfg.mlflow.tracking_uri)
    mlflow.set_experiment(cfg.mlflow.experiment)

    live_path = _live_metrics_path(output_dir)
    # Truncate any previous run's metrics so the UI tail starts clean.
    if live_path is not None:
        live_path.parent.mkdir(parents=True, exist_ok=True)
        live_path.write_text("")
    _write_live_metric(
        live_path,
        {
            "event": "start",
            "timestamp": time.time(),
            "epochs": epochs,
            "backbone": cfg.model.backbone,
        },
    )

    best_f1, bad_epochs = -1.0, 0
    patience = cfg.train.early_stopping.patience

    with mlflow.start_run():
        mlflow.log_params(
            {
                "backbone": cfg.model.backbone,
                "fusion": cfg.model.fusion,
                "num_views": cfg.model.num_views,
                "epochs": epochs,
                "batch_size": cfg.train.batch_size,
                "lr": cfg.train.optimizer.lr,
                "seed": cfg.seed,
            }
        )
        for epoch in range(epochs):
            train_loss = _train_epoch(model, train_dl, criterion, optimizer, device)
            scheduler.step()
            metrics = _validate(model, val_dl, device, num_classes)
            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "val_macro_f1": metrics["macro_f1"],
                    "val_accuracy": metrics["accuracy"],
                },
                step=epoch,
            )
            print(
                f"epoch {epoch + 1}/{epochs}  loss={train_loss:.4f}  "
                f"val_macro_f1={metrics['macro_f1']:.4f}  "
                f"val_acc={metrics['accuracy']:.4f}"
            )
            _write_live_metric(
                live_path,
                {
                    "event": "epoch",
                    "timestamp": time.time(),
                    "epoch": epoch + 1,
                    "epochs": epochs,
                    "train_loss": train_loss,
                    "val_macro_f1": metrics["macro_f1"],
                    "val_accuracy": metrics["accuracy"],
                },
            )

            if metrics["macro_f1"] > best_f1:
                best_f1, bad_epochs = metrics["macro_f1"], 0
                torch.save(
                    {
                        "model": model.state_dict(),
                        "num_classes": num_classes,
                        "class_names": taxonomy.class_names(),
                        "model_cfg": OmegaConf.to_container(cfg.model, resolve=True),
                        "image_size": cfg.data.image_size,
                        "config": OmegaConf.to_container(cfg, resolve=True),
                    },
                    ckpt_path,
                )
            else:
                bad_epochs += 1
                if bad_epochs >= patience:
                    print(f"early stopping at epoch {epoch + 1}")
                    break

        mlflow.log_metric("best_val_macro_f1", best_f1)
        if ckpt_path.is_file():
            mlflow.log_artifact(str(ckpt_path))

    _write_live_metric(
        live_path,
        {"event": "done", "timestamp": time.time(), "best_val_macro_f1": best_f1},
    )
    print(f"\nbest val macro-F1: {best_f1:.4f}  ->  {ckpt_path}")
    return ckpt_path
