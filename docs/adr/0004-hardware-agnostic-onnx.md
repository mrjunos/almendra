# ADR-0004: Hardware-agnostic deployment via ONNX

- **Status:** Accepted
- **Date:** 2026-05-19

## Context
The model must eventually run "as fast as physics allows" on a sorting machine
**that does not exist yet** — the target accelerator is unknown. Committing early
to a vendor runtime (TensorRT, Coral, …) would couple the model to hardware that
has not been chosen.

## Decision
Commit to a **portable intermediate representation, not a chip**:

1. Train in PyTorch.
2. Export to **ONNX** with a pinned opset and a dynamic batch axis.
3. Apply **INT8 static post-training quantization** with a calibration set.
4. Compile *late* for whatever accelerator is selected (TensorRT / OpenVINO /
   Coral / ONNX Runtime execution providers).

Every export runs a **numerical parity check** against the source PyTorch model
(FP32 and INT8) within a configured tolerance.

The toolchain around this: **uv** (environment), **Hydra** (config-driven runs),
**DVC** (data versioning), **MLflow** (experiment tracking).

## Consequences
- The model is never coupled to one vendor; the hardware decision is deferred
  until there is data to benchmark on (Phase 5).
- The model stays small and quantization-friendly regardless of how powerful the
  final accelerator is — speed headroom is never wasted.
- ONNX opset and quantization mode are config (`configs/export/`), not code.
- A parity-check failure blocks a release — a silently wrong export cannot ship.
