"""Export a trained checkpoint to ONNX, then optionally quantize to INT8.

Every float export is checked for numerical parity against the source PyTorch
model — a silently wrong export must not ship.

Phase 1 uses dynamic INT8 quantization (robust, no calibration set, ~4x smaller
weights). Static PTQ with a calibration set — better for raw speed — is a
Phase 5 task (see docs/research-log.md).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from almendra.models.classifier import build_model
from almendra.taxonomy import get_taxonomy


def export_onnx(
    model, num_views: int, image_size: int, path: Path, opset: int, dynamic_batch: bool
) -> None:
    model.eval()
    dummy = torch.randn(1, num_views, 3, image_size, image_size)
    dynamic_axes = {"views": {0: "batch"}, "logits": {0: "batch"}} if dynamic_batch else None
    # dynamo=False: the stable TorchScript exporter. Its graph is what the ONNX
    # Runtime quantization tooling reliably consumes; the newer dynamo exporter
    # currently emits shape metadata the quantizer's shape inference rejects.
    torch.onnx.export(
        model,
        dummy,
        str(path),
        input_names=["views"],
        output_names=["logits"],
        opset_version=opset,
        dynamic_axes=dynamic_axes,
        dynamo=False,
    )


def check_parity(
    model, onnx_path: Path, num_views: int, image_size: int, num_samples: int
) -> float:
    """Return the max absolute logit difference between PyTorch and ONNX Runtime."""
    import onnxruntime as ort

    model.eval()
    x = torch.randn(num_samples, num_views, 3, image_size, image_size)
    with torch.no_grad():
        torch_out = model(x).numpy()
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_out = session.run(["logits"], {"views": x.numpy()})[0]
    return float(np.abs(torch_out - onnx_out).max())


def quantize_int8_dynamic(float_path: Path, int8_path: Path) -> None:
    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(str(float_path), str(int8_path), weight_type=QuantType.QInt8)


def run(cfg, checkpoint: str | None = None) -> dict:
    """Export the checkpoint to ONNX (+ optional INT8); return the artifact paths."""
    num_classes = get_taxonomy().num_defect_classes
    ckpt_path = Path(checkpoint) if checkpoint else Path(cfg.output_dir) / "best.pt"
    if not ckpt_path.is_file():
        raise FileNotFoundError(f"checkpoint not found: {ckpt_path}")

    model = build_model(cfg.model, num_classes)
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model"])
    model.eval()

    num_views = cfg.model.num_views
    image_size = cfg.data.image_size
    out_dir = ckpt_path.parent
    float_path = out_dir / "model.onnx"

    export_onnx(
        model,
        num_views,
        image_size,
        float_path,
        cfg.export.opset,
        cfg.export.dynamic_batch,
    )
    print(f"exported ONNX -> {float_path}")

    if cfg.export.parity.enabled:
        max_diff = check_parity(
            model, float_path, num_views, image_size, cfg.export.parity.num_samples
        )
        tol = cfg.export.parity.tolerance
        passed = max_diff <= tol
        print(
            f"parity check: max abs logit diff = {max_diff:.2e}  "
            f"(tolerance {tol:.0e})  ->  {'PASS' if passed else 'FAIL'}"
        )
        if not passed:
            raise RuntimeError("ONNX parity check failed — export aborted")

    result = {"float_onnx": str(float_path)}
    if cfg.export.quantize.enabled:
        int8_path = out_dir / "model.int8.onnx"
        # Quantization is the flakier step — never let it sink a valid float export.
        try:
            quantize_int8_dynamic(float_path, int8_path)
        except Exception as exc:  # noqa: BLE001
            print(f"INT8 quantization skipped: {exc}")
        else:
            float_mb = float_path.stat().st_size / 1e6
            int8_mb = int8_path.stat().st_size / 1e6
            print(f"quantized INT8 -> {int8_path}  ({float_mb:.2f} MB -> {int8_mb:.2f} MB)")
            result["int8_onnx"] = str(int8_path)
    return result
