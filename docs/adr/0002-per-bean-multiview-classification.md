# ADR-0002: Per-bean, multi-view, multi-spectral classification

- **Status:** Accepted
- **Date:** 2026-05-19

## Context
The model must classify green coffee beans for a high-throughput sorting machine
and must not miss damage hidden from a single viewpoint. Candidate framings:
single-image classification, multi-bean object detection, or a per-bean classifier
fed multiple images.

## Decision
The task is **per-bean classification**, where one sample is a **set of images**
of a single bean — multiple viewing angles × multiple illumination spectra
(front-light, back-light, UV) — fused by the model into one decision.

Rejected alternatives:
- **Single-image classification** — a defect on an unseen face is missed.
- **Multi-bean detection (YOLO-style)** — heavier, harder to evaluate rigorously,
  and a high-volume machine singulates beans regardless; the per-bean decision is
  what actually drives the ejector.

## Consequences
- The dataset unit is a bean (a set of views), not an image — see the manifest
  design in `src/almendra/datasets/`.
- The model is a shared-backbone multi-view network with a fusion head.
- Training uses **view-dropout** so the model tolerates a variable view count —
  enabling "collect rich, deploy lean" (slow exhaustive Rig A, fast Rig B).
- Public datasets are mostly single-view; true multi-view validation depends on
  proprietary capture (Phase 3).
