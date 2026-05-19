"""Benchmark ONNX inference latency and throughput.

Reports warmed-up p50/p95/p99 latency across the available ONNX Runtime
execution providers — the basis of the Phase 5 hardware comparison. The model
must never be the throughput bottleneck (see docs/methodology.md).
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np


def benchmark(
    onnx_path: Path,
    num_views: int,
    image_size: int,
    batch_size: int = 1,
    warmup: int = 20,
    iters: int = 200,
    providers: list[str] | None = None,
) -> dict:
    """Benchmark `onnx_path` on each requested (and available) execution provider."""
    import onnxruntime as ort

    available = ort.get_available_providers()
    chosen = [p for p in (providers or available) if p in available]
    x = np.random.randn(batch_size, num_views, 3, image_size, image_size).astype(np.float32)

    results: dict[str, dict] = {}
    for provider in chosen:
        session = ort.InferenceSession(str(onnx_path), providers=[provider])
        feed = {session.get_inputs()[0].name: x}
        for _ in range(warmup):
            session.run(None, feed)

        samples = []
        for _ in range(iters):
            start = time.perf_counter()
            session.run(None, feed)
            samples.append((time.perf_counter() - start) * 1000.0)
        samples.sort()

        mean_ms = sum(samples) / len(samples)
        results[provider] = {
            "p50_ms": samples[int(0.50 * iters)],
            "p95_ms": samples[int(0.95 * iters)],
            "p99_ms": samples[min(int(0.99 * iters), iters - 1)],
            "mean_ms": mean_ms,
            "throughput_beans_s": batch_size * 1000.0 / mean_ms,
        }
    return results


def run(cfg, model_path: str | None = None) -> dict:
    """Benchmark an exported ONNX model and print a latency table."""
    path = Path(model_path) if model_path else Path(cfg.output_dir) / "model.onnx"
    if not path.is_file():
        raise FileNotFoundError(f"ONNX model not found: {path} — run `almendra export` first")

    results = benchmark(path, cfg.model.num_views, cfg.data.image_size, batch_size=1)
    print(f"\n=== latency benchmark: {path.name} (batch=1) ===")
    print(f"{'provider':<26} {'p50_ms':>8} {'p95_ms':>8} {'p99_ms':>8} {'beans/s':>9}")
    for provider, r in results.items():
        print(
            f"{provider:<26} {r['p50_ms']:>8.2f} {r['p95_ms']:>8.2f} "
            f"{r['p99_ms']:>8.2f} {r['throughput_beans_s']:>9.0f}"
        )
    return results
