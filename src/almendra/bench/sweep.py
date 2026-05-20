"""Backbone sweep — train, eval, export (static INT8), bench across backbones.

Produces a results CSV and a Pareto markdown table to characterise the
accuracy / latency / model-size frontier (RQ3, RQ4).
"""

from __future__ import annotations

import csv
from pathlib import Path

from omegaconf import OmegaConf


def _bench_summary(latencies: dict) -> tuple[dict | None, str | None]:
    """Pick a single provider's numbers — prefer CPU for portability."""
    if not latencies:
        return None, None
    provider = (
        "CPUExecutionProvider" if "CPUExecutionProvider" in latencies else next(iter(latencies))
    )
    return latencies[provider], provider


def run_one(base_cfg, backbone: str, epochs: int, out_root: Path) -> dict:
    """Train, eval, export and bench one backbone; return a results row."""
    from almendra.bench import latency as latency_mod
    from almendra.eval import evaluate
    from almendra.export import exporter as export_mod
    from almendra.train import loop as train_loop

    # Deep copy the config so per-backbone overrides do not leak across runs.
    cfg = OmegaConf.create(OmegaConf.to_container(base_cfg, resolve=True))
    cfg.model.backbone = backbone
    cfg.model.name = backbone
    cfg.train.epochs = epochs
    cfg.output_dir = str(out_root / backbone)

    print(f"\n=== sweep: {backbone} ({epochs} epochs) ===")
    ckpt = train_loop.run(cfg)
    test_metrics = evaluate.run(cfg, checkpoint=str(ckpt), split="test")
    artifacts = export_mod.run(cfg, checkpoint=str(ckpt))

    float_path = Path(artifacts["float_onnx"])
    int8_path = Path(artifacts["int8_onnx"]) if "int8_onnx" in artifacts else None
    float_lat = latency_mod.benchmark(float_path, cfg.model.num_views, cfg.data.image_size)
    int8_lat = (
        latency_mod.benchmark(int8_path, cfg.model.num_views, cfg.data.image_size)
        if int8_path
        else {}
    )
    float_stats, provider = _bench_summary(float_lat)
    int8_stats, _ = _bench_summary(int8_lat)

    return {
        "backbone": backbone,
        "test_accuracy": round(test_metrics["accuracy"], 4),
        "test_macro_f1": round(test_metrics["macro_f1"], 4),
        "missed_defect": round(test_metrics["missed_defect_rate"], 4),
        "float_size_mb": round(float_path.stat().st_size / 1e6, 2),
        "int8_size_mb": (round(int8_path.stat().st_size / 1e6, 2) if int8_path else None),
        "float_p50_ms": round(float_stats["p50_ms"], 2) if float_stats else None,
        "float_throughput": (round(float_stats["throughput_beans_s"], 0) if float_stats else None),
        "int8_p50_ms": round(int8_stats["p50_ms"], 2) if int8_stats else None,
        "int8_throughput": (round(int8_stats["throughput_beans_s"], 0) if int8_stats else None),
        "bench_provider": provider,
    }


def run(base_cfg, backbones: list[str], epochs: int, out_root: str | Path) -> list[dict]:
    """Run the sweep across `backbones`; write CSV + Pareto markdown."""
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    rows = [run_one(base_cfg, backbone, epochs, out_root) for backbone in backbones]
    _write_csv(rows, out_root / "results.csv")
    _write_markdown(rows, out_root / "pareto.md", epochs)
    print(f"\nsweep complete -> {out_root}/results.csv  +  pareto.md")
    return rows


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows: list[dict], path: Path, epochs: int) -> None:
    columns = [
        ("backbone", "backbone"),
        ("test_macro_f1", "test mF1"),
        ("missed_defect", "missed-def"),
        ("float_size_mb", "float MB"),
        ("int8_size_mb", "int8 MB"),
        ("float_p50_ms", "float p50 ms"),
        ("int8_p50_ms", "int8 p50 ms"),
        ("int8_throughput", "int8 beans/s"),
    ]
    with path.open("w") as fh:
        fh.write(f"# Backbone sweep — {epochs} epochs, static INT8 PTQ\n\n")
        fh.write("| " + " | ".join(label for _, label in columns) + " |\n")
        fh.write("|" + "|".join("---" for _ in columns) + "|\n")
        for row in rows:
            cells = []
            for key, _ in columns:
                value = row.get(key)
                cells.append("—" if value is None else str(value))
            fh.write("| " + " | ".join(cells) + " |\n")
        provider = rows[0].get("bench_provider", "unknown") if rows else "unknown"
        fh.write(f"\nBench provider: `{provider}` (batch 1).\n")
