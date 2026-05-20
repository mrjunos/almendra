"""Export a trained checkpoint to ONNX, then optionally quantize to INT8.

Every float export is checked for numerical parity against the source PyTorch
model — a silently wrong export must not ship.

Two quantization modes are supported (``cfg.export.quantize.mode``):

- ``int8_dynamic`` — weights only, no calibration; robust, modest speed-up.
- ``int8_static`` — weights + activations via PTQ with a calibration set of
  real bean images drawn from the train split; smaller and usually faster on
  CPU. Default for Phase 5.
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


def quantize_int8_static(float_path: Path, int8_path: Path, calibration_reader) -> None:
    """Static post-training quantization using a real-image calibration set."""
    from onnxruntime.quantization import (
        CalibrationMethod,
        QuantFormat,
        QuantType,
        quantize_static,
    )
    from onnxruntime.quantization.shape_inference import quant_pre_process

    prepped = float_path.with_suffix(".prep.onnx")
    quant_pre_process(str(float_path), str(prepped))
    # QUInt8 activations: ReLU produces non-negative values; symmetric INT8
    # wastes half its range. per_channel=True: each Conv weight channel gets its
    # own scale, recovering accuracy MobileNet-style backbones otherwise lose.
    quantize_static(
        str(prepped),
        str(int8_path),
        calibration_reader,
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        calibrate_method=CalibrationMethod.MinMax,
        per_channel=True,
    )
    prepped.unlink(missing_ok=True)


def _build_calibration_reader(cfg):
    """Build an ONNX Runtime calibration reader from the train split."""
    from onnxruntime.quantization.calibrate import CalibrationDataReader

    from almendra.datasets.manifest import filter_split, read_manifest
    from almendra.datasets.multiview import MultiViewBeanDataset
    from almendra.datasets.transforms import build_transforms
    from almendra.paths import processed_dir

    class _BeanReader(CalibrationDataReader):
        def __init__(self, records, transform, num_views, root):
            super().__init__()
            dataset = MultiViewBeanDataset(records, transform, num_views, 0.0, root=root)
            self._iter = iter(dataset)

        def get_next(self):
            try:
                views, _ = next(self._iter)
            except StopIteration:
                return None
            return {"views": views.unsqueeze(0).numpy().astype(np.float32)}

    manifest = processed_dir() / "manifest.jsonl"
    records = filter_split(read_manifest(manifest), "train")
    # Shuffle deterministically so the calibration set covers the class
    # distribution evenly, not just whatever classes appear first in the manifest.
    import random as _random

    _random.Random(42).shuffle(records)
    n_samples = cfg.export.quantize.get("calibration_samples", 100)
    transform = build_transforms(cfg.data.image_size, None, train=False)
    return _BeanReader(records[:n_samples], transform, cfg.model.num_views, processed_dir())


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
        mode = cfg.export.quantize.get("mode", "int8_dynamic")
        int8_path: Path | None = out_dir / "model.int8.onnx"
        # Quantization is the flakier step — never let it sink a valid float export.
        try:
            if mode == "int8_dynamic":
                quantize_int8_dynamic(float_path, int8_path)
            elif mode == "int8_static":
                quantize_int8_static(float_path, int8_path, _build_calibration_reader(cfg))
            elif mode == "none":
                int8_path = None
            else:
                raise ValueError(f"unknown quantize mode: {mode}")
        except Exception as exc:  # noqa: BLE001
            print(f"INT8 quantization skipped: {exc}")
            int8_path = None
        if int8_path is not None:
            float_mb = float_path.stat().st_size / 1e6
            int8_mb = int8_path.stat().st_size / 1e6
            print(
                f"quantized INT8 ({mode}) -> {int8_path}  ({float_mb:.2f} MB -> {int8_mb:.2f} MB)"
            )
            result["int8_onnx"] = str(int8_path)
    return result
