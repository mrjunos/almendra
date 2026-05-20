"""Filesystem discovery helpers — find runs, checkpoints, manifests.

The UI is stateless across reruns; everything it shows comes from the disk
layout under ``outputs/`` and ``data/processed/``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    """Walk up from CWD looking for ``pyproject.toml``; fall back to CWD."""
    here = Path.cwd().resolve()
    for parent in (here, *here.parents):
        if (parent / "pyproject.toml").is_file():
            return parent
    return here


def outputs_root() -> Path:
    return project_root() / "outputs"


def manifest_path() -> Path:
    return project_root() / "data" / "processed" / "manifest.jsonl"


@dataclass(frozen=True)
class RunInfo:
    """One training run on disk."""

    name: str
    path: Path
    checkpoint: Path | None
    metrics: Path | None
    onnx_float: Path | None
    onnx_int8: Path | None
    modified_at: float


def list_runs() -> list[RunInfo]:
    """All run dirs under ``outputs/`` that contain at least a metrics file or checkpoint."""
    root = outputs_root()
    if not root.is_dir():
        return []
    runs: list[RunInfo] = []
    for path in sorted(root.iterdir()):
        if not path.is_dir():
            continue
        ckpt = path / "best.pt"
        metrics = path / "live_metrics.jsonl"
        float_onnx = path / "model.onnx"
        int8_onnx = path / "model.int8.onnx"
        if not (ckpt.is_file() or metrics.is_file() or float_onnx.is_file()):
            continue
        runs.append(
            RunInfo(
                name=path.name,
                path=path,
                checkpoint=ckpt if ckpt.is_file() else None,
                metrics=metrics if metrics.is_file() else None,
                onnx_float=float_onnx if float_onnx.is_file() else None,
                onnx_int8=int8_onnx if int8_onnx.is_file() else None,
                modified_at=path.stat().st_mtime,
            )
        )
    return sorted(runs, key=lambda r: r.modified_at, reverse=True)


def best_onnx_for_prediction() -> Path | None:
    """Most-recently-modified ONNX (prefer INT8) across all runs."""
    candidates: list[Path] = []
    for run in list_runs():
        if run.onnx_int8:
            candidates.append(run.onnx_int8)
        if run.onnx_float:
            candidates.append(run.onnx_float)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)
