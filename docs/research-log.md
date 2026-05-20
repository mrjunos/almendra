# Research Log

almendra is run as a rigorous investigation. This log tracks the research
questions, open uncertainties, and a dated record of decisions and findings.

## Research questions

| ID | Question | Metric | Status |
|----|----------|--------|--------|
| RQ1 | Does multi-view fusion lower the missed-defect rate vs a single best view? | Missed-defect rate, per class | Open — needs real multi-view (tray) data |
| RQ2 | Does multi-spectral illumination (UV, transillumination) catch defects RGB front-light misses? | Per-class recall delta | Open — needs Phase 4 |
| RQ3 | What is the accuracy / latency / model-size Pareto frontier across backbones? | Macro-F1 vs p95 latency vs MB | Partially answered (Phase 5) — 3 torchvision backbones; timm variants deferred |
| RQ4 | What accuracy is lost to INT8 quantization, per class? | Per-class F1 delta (FP32→INT8) | Answered (Phase 5) — per-backbone macro-F1 delta; MN3-Small needs dynamic / QAT |
| RQ5 | How few deployment views keep per-class recall acceptable? | Recall vs view count | Partially answered (Phase 2) — view-count robustness shown on pseudo-views |

## Open uncertainties / TODO

- [ ] **Verify the SCA `full_defect_equivalent` table** in `data/taxonomy.yaml`
      against the official SCA Arabica Green Coffee Defect Handbook. Currently
      marked `verified: false`.
- [ ] **USK-COFFEE host reachability** — research found the portal timing out;
      confirm a working download path before relying on it.
- [ ] **Kaggle 17-defects licence** — unstated. Do not ingest until confirmed;
      then fill the empty `class_map` in `data/sources/kaggle_17defects.yaml`.
- [ ] Choose the fusion-head default (attention vs gated) — both are implemented;
      decide on real multi-view data, or as part of the Phase 5 sweep.
- [ ] Recover MobileNetV3-Small INT8 accuracy via QAT or use dynamic INT8 as the
      fallback for that backbone — static PTQ collapses (h-swish + per-tensor
      MinMax). See the Phase 5 log entry.
- [ ] Extend the backbone sweep with timm variants (efficientnet_lite0,
      ghostnet, mobileone) to fill out the Pareto frontier.

## Findings carried in from pre-project research

Three background research sweeps informed the plan (datasets, SOTA models,
deployment tooling). Headline findings:

- **Verified:** YOLOv10-N reached ~0.992 precision on green-bean micro-defects
  (Bangladesh study); a MobileNetV3 + Tiny-YOLOv8 edge framework reached 96.8 %
  at < 150 ms on a Raspberry Pi.
- **Unverified:** specific YOLOv8-vs-YOLOv11 USK-COFFEE mAP claims and a
  YOLOv12-for-SCA-defects study could not be confirmed in published literature.
- **Datasets:** no large, cleanly-licensed Arabica defect dataset exists; most
  public data is Robusta. This shaped the dual-track data strategy.

## Log

### 2026-05-21 — Phase 6: local Streamlit UI

- **New optional-deps group `ui`** (`streamlit`, `plotly`) and `almendra ui`
  CLI subcommand that exec's `streamlit run` on `src/almendra/ui/app.py`. `make
  ui` is the matching shortcut.
- **Six pages** behind a sidebar radio: Home (dataset stats + recent runs +
  inline wizard), Tray Capture, Train, Evaluate, Predict, Settings.
- **Bilingual ES/EN from day one** — every visible string lives in a central
  dict (`ui/components/i18n.py`) and pages read it through `t("key", lang)`. A
  sidebar radio toggles the language; adding a third language is a translation
  job, not a rewrite. Default: Spanish.
- **Live training charts** — `train.loop` writes one JSONL line per epoch to
  `outputs/<run>/live_metrics.jsonl` (controlled by env var
  `ALMENDRA_LIVE_METRICS` so the CLI use case is untouched). The Train page
  launches training as a subprocess, polls the file every ~2 s, and re-renders
  a two-line Plotly chart (train_loss + val_macro_f1).
- **Decoupled, file-based contract** — the UI is stateless across reruns;
  everything it shows (runs, checkpoints, ONNX, metrics) is discovered from
  disk under `outputs/`. Anything that writes the same JSONL schema works with
  the UI.
- **Inline wizard** on Home with three "press to go" buttons that walk
  Ingest → Train → Eval with sensible defaults. Advanced controls (gated
  fusion, view-dropout, augmentation toggles) live behind an `Advanced`
  expander on the Train page so they don't intimidate first-time users.
- **Tests** — `streamlit.testing.v1.AppTest` smoke-tests render every page in
  ES *and* EN (12 cases) without exceptions; the i18n dict is checked for
  complete coverage; the live-metrics JSONL writer/reader has its own unit
  test. All 45 tests in the suites that don't require torch/onnxruntime pass.
- **Scope split** — Phase 6.0 (this PR) ships the six pages, the CLI/Make
  entrypoints and tests. Phase 6.1 will add: a dedicated **Labelling** page
  with hotkeys + IAA reporting, an **Export & Bench** page, a model-package
  zip exporter, and a "Demo mode" using the public Roboflow data.

### 2026-05-20 — Phase 5: backbone sweep + static INT8 PTQ

- Static INT8 PTQ implemented (`quantize_int8_static` in `src/almendra/export/exporter.py`):
  ONNX Runtime per-channel weight quantization with QUInt8 activations and a
  shuffled real-image calibration set drawn from the train split. Default mode
  in `configs/export/onnx_int8.yaml`.
- Backbone sweep runner (`almendra sweep` / `make sweep`) — train → eval →
  export → bench per backbone, with a CSV + Pareto markdown report.
- CI Node-20 actions bumped to `actions/checkout@v5` + `setup-uv@v6`.

**Pareto sweep** — MobileNetV3-Small / MobileNetV3-Large / EfficientNet-B0
(20 epochs each, single-view, ONNX Runtime CPU EP, batch 1, test split 62 beans):

| backbone | FP32 mF1 | INT8 mF1 | mF1 loss | FP32 MB | INT8 MB | FP32 p50 ms | INT8 p50 ms | INT8 beans/s |
|---|---|---|---|---|---|---|---|---|
| mobilenet_v3_small | 0.894 | **0.034** | **−0.860** | 4.06 | 1.37 | 2.12 | 1.22 | 812 |
| mobilenet_v3_large | 0.939 | 0.860 | −0.079 | 12.45 | 3.63 | 5.50 | 2.34 | 427 |
| efficientnet_b0 | 0.895 | 0.714 | −0.182 | 16.78 | 5.13 | 10.03 | 4.63 | 216 |

**RQ3 (Pareto frontier across backbones):**
- **MobileNetV3-Large is the clear winner**: the highest FP32 accuracy (0.939),
  retains healthy accuracy under INT8 (0.860), and runs at 427 beans/s in 3.6 MB
  on a single CPU thread.
- MobileNetV3-Small holds the FP32 speed/size corner (1.37 MB INT8, 1.2 ms) but
  its INT8 is broken as currently quantized.
- EfficientNet-B0 is **dominated** here: larger, slower, and lower FP32 accuracy
  than MobileNetV3-Large.

**RQ4 (INT8 accuracy cost):** static PTQ (per-channel weights, QUInt8
activations, MinMax calibration over 100 shuffled train images):

- **MobileNetV3-Small — catastrophic (−86 mF1 points).** Matches a known failure
  mode: MN3-Small's *hardswish* activation has a range MinMax calibration cannot
  pin down cleanly with per-tensor activation scales, and the per-channel fix
  that rescues Conv-heavy networks does not transfer. Use **dynamic INT8**
  (`mode: int8_dynamic`, weights only) for this backbone, or do QAT.
- MobileNetV3-Large — −8 mF1 points: acceptable trade for 3.4× smaller and 2.4×
  faster.
- EfficientNet-B0 — −18 mF1 points: sub-acceptable. Either keep FP32 or pick a
  Conv-cleaner backbone.

**Concrete deployment recommendation today**: MobileNetV3-Large + static INT8
PTQ — **0.86 INT8 macro-F1, 3.63 MB, ~430 beans/s on a single CPU thread**.

**Caveats:** missed-defect rate ties at 0.047 (3 of 62 beans) across FP32
models — the test set is too small to differentiate that metric. The relative
ranking and the INT8 dynamics are the real signal here.

### 2026-05-19 — Phase 2: multi-view model + view-count robustness
- The multi-view fusion model is exercised end-to-end via **pseudo-views** —
  distinct fixed orientations of a single-view bean
  (`almendra.datasets.pseudoview`), an honest stand-in until the tray rig
  produces real multi-view data.
- Added gated attention fusion (Ilse et al.) alongside mean / max / attention.
- **Multi-view run** — MobileNetV3-Small, 4 pseudo-views, attention fusion,
  view-dropout 0.3, 25 epochs: validation macro-F1 **0.922**.
- **View-count robustness (RQ5)** — the same checkpoint evaluated at 1/2/4 views:

  | views | test accuracy | test macro-F1 | missed-defect |
  |-------|---------------|---------------|---------------|
  | 1 | 0.919 | 0.928 | 0.047 |
  | 2 | 0.919 | 0.928 | 0.047 |
  | 4 | 0.903 | 0.917 | 0.047 |

  Trained on 4 views with view-dropout, the model performs equivalently at any
  view count — validating "collect rich, deploy lean".
- **Honest caveat:** pseudo-views are orientations of the *same* image, so extra
  views carry no new information — multi-view here behaves as test-time
  augmentation. RQ1 (does the bean's hidden *face* lower the missed-defect rate)
  is untouched and needs real tray data.

### 2026-05-19 — Tray batch-capture segmentation
- Added the gridded-tray auto-segmentation pipeline (`src/almendra/datasets/tray.py`)
  and the `almendra tray-check` command: photograph a tray of beans, flip it,
  photograph again — the software rectifies each photo via corner ArUco markers,
  crops every well, and pairs the two sides into multi-view beans by well address.
- Capture protocol (`capture/`) rewritten around batch tray capture (see
  ADR-0005), replacing per-bean singulation as the Rig A method.
- The structured `format: tray` source ingester (sessions + labels → manifest)
  remains a Phase 3 task.

### 2026-05-19 — Phase 1: data pipeline + single-view baseline
- Roboflow Robusta defects dataset (v2, 1507 images) downloaded and ingested:
  COCO instances cropped to single-bean images → `data/processed/manifest.jsonl`
  (1507 beans across 7 of the 18 canonical classes).
- Full pipeline implemented and run end-to-end — `ingest → train → eval →
  export → bench` — driven by Hydra config and the `almendra` CLI.
- **Baseline** — MobileNetV3-Small, single-view, 30 epochs, seed 42:
  - validation macro-F1 **0.936**
  - **test**: accuracy **0.919**, macro-F1 **0.921**, missed-defect rate **0.047**
  - per-class test F1: full_black / broken / hull_husk 1.00, sound 0.95,
    severe_insect_damage 0.93, immature 0.84, defect_unspecified 0.73
- ONNX export passes the numerical parity check (max logit diff 1.3e-5); INT8
  dynamic quantization shrinks the model 4.06 MB → 1.20 MB.
- Latency (ONNX Runtime, CPU, batch 1): p50 ≈ 2.1 ms, ≈ 470 beans/s — the model
  is far from the throughput bottleneck, as intended.
- **Caveat:** this baseline is **Robusta** public data with partly coarse labels
  (`defect_unspecified`). It validates the *framework* end-to-end — it is not the
  final Arabica model.

### 2026-05-19 — Phase 0: scaffolding
- Repository created: `github.com/mrjunos/almendra` (Apache-2.0).
- Canonical taxonomy drafted (`data/taxonomy.yaml`): 18 defect classes
  (SCA-aligned, **provisional**) + 4 morphology classes.
- Dataset adapters declared for 5 public datasets (`data/sources/`).
- Toolchain fixed: uv + Hydra + DVC + MLflow + ONNX (see ADR-0004).
- Package skeleton, CLI (`almendra info`), tests and CI in place.
- Capture protocol for Rig A documented (`capture/`).

<!-- New entries go on top, newest first. -->
