"""Tests for static INT8 post-training quantization."""

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization.calibrate import CalibrationDataReader

from almendra.export.exporter import export_onnx, quantize_int8_static
from almendra.models.classifier import MultiViewClassifier


class _SyntheticReader(CalibrationDataReader):
    """Calibration reader yielding random tensors of the model's input shape."""

    def __init__(self, n: int, num_views: int, image_size: int):
        super().__init__()
        self._iter = iter(
            {"views": np.random.randn(1, num_views, 3, image_size, image_size).astype(np.float32)}
            for _ in range(n)
        )

    def get_next(self):
        return next(self._iter, None)


def test_quantize_int8_static_end_to_end(tmp_path):
    model = MultiViewClassifier("mobilenet_v3_small", num_classes=18, pretrained=False)
    float_path = tmp_path / "model.onnx"
    int8_path = tmp_path / "model.int8.onnx"

    export_onnx(model, num_views=1, image_size=96, path=float_path, opset=17, dynamic_batch=True)
    quantize_int8_static(float_path, int8_path, _SyntheticReader(8, 1, 96))

    assert int8_path.is_file()
    assert int8_path.stat().st_size < float_path.stat().st_size, "INT8 must be smaller than FP32"

    # the int8 model loads and produces the expected output shape
    session = ort.InferenceSession(str(int8_path), providers=["CPUExecutionProvider"])
    x = np.random.randn(1, 1, 3, 96, 96).astype(np.float32)
    out = session.run(["logits"], {"views": x})[0]
    assert out.shape == (1, 18)
