"""Model export (Phase 1).

Planned modules
---------------
  to_onnx.py   PyTorch -> ONNX (pinned opset, dynamic batch axis).
  quantize.py  INT8 static post-training quantization with a calibration set.
  parity.py    numerical parity check of the exported model vs the source.
"""
