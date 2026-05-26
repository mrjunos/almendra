# ADR-0006: Centralized bean catalog (SQLite, multi-label, provenance-aware)

- **Status:** Accepted
- **Date:** 2026-05-26

## Context
The data is the project's core value, but it was stored as a flat JSONL manifest
(`data/processed/manifest.jsonl`) with one defect per bean, no per-bean
provenance (farm, variety, altitude, process, dates, humidity), no separation of
public datasets from the user's own private data, and no record of where a label
came from. Real beans can carry more than one defect, and the dataset pool will
grow (public sets now; proprietary Arabica capture later).

## Decision
Introduce a **centralized catalog** as the source of truth, alongside the images
on disk:

- **Backend:** SQLite now, **Postgres-portable** via SQLModel (typed
  SQLAlchemy + Pydantic). The catalog stores paths + labels + metadata; image
  files stay on disk under `data/processed/`. The catalog stays small as data
  grows because the heavy payload (images) is not in the DB.
- **Multi-label by construction:** defects live in a `bean_defect` junction
  (bean ↔ defect), so a bean may carry several defects. `is_primary` marks the
  SCA most-severe one for grading and single-label export.
- **Provenance on `lot`:** a lot is a batch sharing origin. Public datasets get
  one synthetic public lot per source (most fields null); private beans get a
  real lot with farm/variety/altitude/process/harvest-wash-hulling dates/humidity.
- **Label trust is explicit:** every `bean_defect` records `label_source`
  (`dataset` / `human_verified` / `model_weak`) and a `trust` score, so weak
  dataset labels and verified labels coexist and can be re-verified over time.
- **Public/private separation:** `lot.provenance_type` (`public_dataset` /
  `proprietary`); export is public-only by default and private is opt-in
  (`--all-provenance`), so the user's data is never silently mixed in.
- **Training stays decoupled:** `almendra db export-manifest` writes the same
  `manifest.jsonl` the loaders already read (now carrying a multi-label
  `defects` list plus the back-compat primary `defect_class`/`defect_index`).
- **Taxonomy contract preserved:** defect/morphology classes are seeded from
  `data/taxonomy.yaml`; indices remain a fixed contract (see ADR-0003).

The catalog file (`data/catalog.db`) is **git-ignored and regenerable** from the
committed manifest + taxonomy via `almendra db migrate`.

## Consequences
- One bean can record several defects without changing the schema again; the
  model migrates to multi-label separately.
- Rich per-bean/per-lot metadata supports later analysis (by farm, altitude,
  variety, process) and clean separation of the high-value private data.
- A schema move to Postgres (multi-user/cloud) is a config change, not a rewrite.
- **DVC deferred:** the plan calls for versioning the image blobs with DVC, but
  no remote is chosen yet and `dvc add` restructures storage. Images remain local
  + git-ignored for now; DVC is set up in a focused follow-up once a remote
  (drive/S3) is picked. The catalog does not depend on it.
