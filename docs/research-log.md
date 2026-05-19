# Research Log

almendra is run as a rigorous investigation. This log tracks the research
questions, open uncertainties, and a dated record of decisions and findings.

## Research questions

| ID | Question | Metric | Status |
|----|----------|--------|--------|
| RQ1 | Does multi-view fusion lower the missed-defect rate vs a single best view? | Missed-defect rate, per class | Open — needs Phase 2 + data |
| RQ2 | Does multi-spectral illumination (UV, transillumination) catch defects RGB front-light misses? | Per-class recall delta | Open — needs Phase 4 |
| RQ3 | What is the accuracy / latency / model-size Pareto frontier across backbones? | Macro-F1 vs p95 latency vs MB | Open — Phase 5 |
| RQ4 | What accuracy is lost to INT8 quantization, per class? | Per-class F1 delta (FP32→INT8) | Open — Phase 5 |
| RQ5 | How few deployment views keep per-class recall acceptable? | Recall vs view count | Open — Phase 5 |

## Open uncertainties / TODO

- [ ] **Verify the SCA `full_defect_equivalent` table** in `data/taxonomy.yaml`
      against the official SCA Arabica Green Coffee Defect Handbook. Currently
      marked `verified: false`.
- [ ] **USK-COFFEE host reachability** — research found the portal timing out;
      confirm a working download path before relying on it.
- [ ] **Kaggle 17-defects licence** — unstated. Do not ingest until confirmed;
      then fill the empty `class_map` in `data/sources/kaggle_17defects.yaml`.
- [ ] Decide the Phase 2 fusion-head default (attention vs gated pooling) once
      multi-view data exists.

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
