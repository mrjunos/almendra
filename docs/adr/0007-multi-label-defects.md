# ADR-0007: Multi-label defect classification

- **Status:** Accepted
- **Date:** 2026-05-26

## Context
A real green-coffee bean can carry **more than one defect** at once (e.g. both
immature *and* insect-damaged). The original model was single-label: a softmax
over the 18 taxonomy classes with a cross-entropy loss, forced to pick exactly
one. The catalog (ADR-0006) already stores every defect per bean, so the model
was the remaining single-label bottleneck.

## Decision
Migrate the classifier to **multi-label**:

- **Output / loss:** keep the 18-way head, but treat each output as an
  independent sigmoid and train with `BCEWithLogitsLoss` + per-class
  `pos_weight` (counters defect imbalance). The output dimension stays = the 18
  taxonomy classes, so the fixed-index contract (ADR-0003) and the checkpoint /
  ONNX format are unchanged.
- **Target:** a multi-hot vector over the 18 classes. `sound` (index 0) is an
  explicit positive when a bean has no defect; a defective bean has its defect
  class(es) set. Legacy single-label records fall back to a one-hot of the
  primary defect, so existing data trains unchanged.
- **Prediction:** `sigmoid(logits) ≥ threshold` (default 0.5) per class →
  a *set* of defects. **Accept/reject** = reject if any reject-worthy (defect)
  class fires.
- **Metrics:** multi-label — per-class precision/recall/F1, macro-F1 over
  present classes, micro-F1, exact-match (subset) accuracy, and the
  **missed-defect rate** (a truly-defective bean predicted as clean — the metric
  that matters most for a sorter). There is no single NxN confusion matrix for
  multi-label; the per-class table replaces it.

## Consequences
- A bean's several defects are now learnable and predictable; the value of the
  multi-defect catalog is realised.
- Public datasets are single-label, so multi-hot targets have ≤1 positive until
  proprietary multi-defect beans arrive — BCE handles this transparently.
- "Accuracy" in the UI now means **exact-match** (all defects right), which is
  stricter than top-1; macro-F1 and missed-defect rate are the headline numbers.
- Threshold (0.5) is a deployable knob: lower it to cut missed defects at the
  cost of false rejects (the sorter's precision/recall trade-off).
