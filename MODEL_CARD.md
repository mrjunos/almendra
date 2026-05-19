# Model Card — almendra green coffee bean classifier

> **Status: no model released yet.** The project is in Phase 0 (scaffolding).
> This card is the template that every released checkpoint must fill in, and it
> states the intended use and limitations up front so they guide development.

## Model details
- **Task:** per-bean classification of green (unroasted) coffee beans into the
  defect taxonomy in `data/taxonomy.yaml`.
- **Input:** a *set* of images of one bean (multiple angles × illumination
  spectra); see [methodology](docs/methodology.md).
- **Architecture:** shared lightweight backbone + multi-view fusion head.
- **Version / training run:** _(filled per release — MLflow run ID, config hash)_

## Intended use
- Pre-screening and grading support for green coffee defect sorting.
- Research into multi-view / multi-spectral bean inspection.

## Out-of-scope use
- **Roasted** coffee classification (trained on green beans only).
- Food-safety certification or any sole-arbiter pass/fail decision without human
  oversight — almendra is decision *support*.
- Species/origin authentication, or any claim beyond the defect taxonomy.

## Training data
- _(filled per release: which `data/sources/*` adapters and proprietary lots,
  with counts per class.)_
- **Known bias:** the public-data baseline is Robusta-heavy; Arabica coverage is
  limited until proprietary capture lands. See `docs/datasheets/`.

## Metrics
- _(filled per release.)_ Reported: per-class precision/recall/F1, **missed-defect
  rate**, confusion matrix, calibration, FP32→INT8 deltas, and latency p50/p95/p99.

## Limitations & ethical considerations
- The defect taxonomy is **provisional** — not yet verified against the official
  SCA handbook.
- Performance depends on capture conditions matching the training rig; a
  different camera/lighting setup may degrade results.
- A classifier error has economic consequences for farmers (good beans rejected,
  defects passed). Missed-defect rate and false-reject rate are reported
  separately so the operating point can be chosen deliberately.

## Licence
Apache-2.0 (code). Released model weights, when published, will state their own
licence and a link to the exact training config and data versions.
