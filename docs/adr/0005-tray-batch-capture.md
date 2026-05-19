# ADR-0005: Batch tray capture with auto-segmentation

- **Status:** Accepted
- **Date:** 2026-05-19

## Context
Proprietary data collection (Phase 3) needs many labelled green coffee beans,
each with views of more than one face. Photographing beans one at a time —
singulate, seat, rotate, shoot — is slow and is the practical bottleneck for
building a dataset. Whatever replaces it must still yield, per bean, paired views
of both sides with reliable correspondence.

## Decision
Capture beans in **batches on a gridded tray**:

- Beans sit one-per-well in a rigid tray with four ArUco markers at its corners.
- A photo is rectified to a canonical frame via the markers (robust to camera
  angle and even handheld shots); each well is then cropped and segmented to a
  single-bean image with classical CV — no per-image annotation, no ML model.
- One side is photographed, the tray is flipped (sandwiched with a second tray),
  the other side is photographed. A bean's **well address `(row, col)` is its
  identity**, so the two views are paired by a fixed permutation — the
  correspondence is arithmetic, not an image-matching problem.
- The permutation (`identity` / `mirror_rows` / `mirror_cols`) is determined once
  per rig by a calibration bean and then fixed.

Implemented in `src/almendra/datasets/tray.py`; run via `almendra tray-check`.

Rejected alternatives:
- **Singulated per-bean capture** — accurate but too slow to build a dataset.
- **Grid-free spread + image registration** — minimal hardware, but matching
  beans across the flip is fragile when beans shift between shots.

## Consequences
- ~50–100 beans are captured per pair of photos instead of one at a time.
- The tray segmentation produces almendra's standard multi-view `BeanRecord`
  (`views=[side_a_crop, side_b_crop]`), so no change to the model or training.
- The rig needs a fabricated gridded tray and printed markers (see
  `capture/bom.md`); the tray surface must be non-green.
- Labelling is done by well address (see `capture/labeling-sop.md`).
- The structured `format: tray` source ingester (sessions, labels → manifest)
  is wired in Phase 3; Phase 1's deliverable is the segmentation tool itself.
