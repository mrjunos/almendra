# Methodology

How almendra is built, and why. This document is the technical rationale behind
the [project plan](../README.md#roadmap); decisions are recorded as ADRs in
[`docs/adr/`](adr/).

## 1. Problem

Classify **green (unroasted) coffee beans** by defect, reliably and fast enough
to run on a high-throughput sorting machine. The defect taxonomy is aligned to
the SCA Arabica Green Coffee Defect Handbook (see [`data/taxonomy.yaml`](../data/taxonomy.yaml)).

## 2. Task formulation — a per-bean, multi-view, multi-spectral set classifier

One **sample = one bean**, represented by a *set* of images: several viewing
**angles** × three illumination **spectra** (front-light, back-light, UV). The
model maps that set to one defect class.

- **Not single-image.** A defect on an unseen face is missed by one photo.
- **Not multi-bean detection.** Detection is heavier, harder to evaluate
  rigorously, and a high-volume machine singulates beans anyway. A per-bean
  decision is exactly what drives the ejector. See [ADR-0002](adr/0002-per-bean-multiview-classification.md).

## 3. Model architecture

```
view 1 ─┐
view 2 ─┤─►  shared backbone  ─►  per-view embeddings  ─►  fusion head  ─►  defect class
view N ─┘    (weights shared)                              (attention)
```

- **Shared lightweight backbone** encodes every view (MobileNetV3-Small baseline;
  EfficientNet/Ghost/ShuffleNet/MobileOne in the Phase 5 sweep). Shared weights
  let all views of all in-flight beans run as one batched tensor.
- **Fusion head** (attention pooling; mean/max as baselines) combines per-view
  embeddings into one per-bean vector → classifier.
- **View-dropout:** training randomly drops views, so the model is robust to a
  variable view count — the key to *collect rich, deploy lean*.
- Output: defect-class probabilities; `accept/reject` and SCA grade are *derived*
  from the taxonomy, not learned separately.

## 4. Speed strategy — "collect rich, deploy lean"

Full-surface coverage and high volume seem to conflict. They are decoupled:

- **Rig A** (data collection) is a gridded tray photographed on both sides —
  many beans per shot, auto-segmented and paired by well address (see
  `capture/protocol.md`, ADR-0005).
- **Rig B** (production) is a free-fall multi-camera strobed curtain — few views,
  very high volume.
- The **same model** serves both, because view-dropout training makes it
  view-count agnostic.

The **model is never the bottleneck**: a tiny INT8 backbone, batched, runs faster
than beans can be singulated or air-jet-ejected. Throughput is won by parallel
lanes and strobed capture — physics, not a bigger GPU.

## 5. Data strategy

- **Dual track.** Public datasets bring the pipeline up immediately; a
  proprietary Arabica capture protocol ([`capture/`](../capture/)) supplies the
  real training set. Capture never blocks pipeline work.
- **Unified schema.** Every dataset's taxonomy maps onto the canonical classes
  via `data/sources/*.yaml`. Datasets are never redistributed.
- **Known gap:** most public data is Robusta; the only sizeable Arabica set has
  coarse labels — documented honestly, and the reason proprietary data matters.

## 6. Evaluation methodology

Rigour means measuring the right things, honestly:

- **Per-class** precision / recall / F1 — not just accuracy (defects are rare and
  imbalanced).
- **Missed-defect rate** — the metric that matters for a sorter: a defect scored
  as `sound`. Reported per class; Category 1 misses are weighted hardest.
- **Confusion matrix** and **calibration** (are confidence scores trustworthy?).
- **Sample grade** — aggregate per-bean predictions into an SCA grade and compare
  to the human grade.
- **Splits** are stratified by class and **grouped** so crops from one source
  image never straddle train/test.
- **Inter-annotator agreement** (Cohen's κ) bounds how good any metric can be.

## 7. Reproducibility

- **Config-driven** (Hydra): every run is one composed config.
- **Seeded:** Python/NumPy/torch seeds logged with each run.
- **Tracked:** MLflow logs config, metrics, environment and artifacts.
- **Data versioned:** DVC ties each dataset state to a git commit.
- **Pinned:** `uv.lock` pins the environment.

## 8. Export & hardware-agnostic deployment

The target machine does not exist yet, so we commit to a **portable IR**, not a
chip: PyTorch → **ONNX** (pinned opset, dynamic batch) → INT8 static
quantization → compile late for whatever accelerator is chosen (TensorRT /
OpenVINO / Coral / …). Every export passes a numerical **parity check** against
the source model. See [ADR-0004](adr/0004-hardware-agnostic-onnx.md).
