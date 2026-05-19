# ADR-0003: SCA-aligned, provisional taxonomy

- **Status:** Accepted (provisional)
- **Date:** 2026-05-19

## Context
The model needs a fixed label schema. The Specialty Coffee Association (SCA)
Arabica Green Coffee Defect Handbook is the industry standard, splitting defects
into Category 1 (primary) and Category 2 (secondary), each with a conversion to
"full defects" used for grading.

## Decision
`data/taxonomy.yaml` is the single source of truth. It defines:
- A **defect axis** — `sound` plus SCA-aligned Category 1/2 defect classes, each
  with an `index`, `category`, `accept` flag and `full_defect_equivalent`.
- A separate **morphology axis** (`normal`, `peaberry`, `longberry`, `elephant`)
  — shape is not a defect and must not inflate the defect rate.
- A `defect_unspecified` catch-all for datasets whose labels only say
  "defective".

Class **indices are immutable**: new classes are only appended, so model outputs
stay comparable across retrains.

The schema is marked **`verified: false`**: the `full_defect_equivalent` values
follow the commonly published SCA table but are **not yet checked against the
official handbook**.

## Consequences
- Verifying the conversion table against the official SCA handbook is a tracked
  task (`docs/research-log.md`) and gates any published grading claim.
- Any taxonomy change bumps `schema_version`; labelled data records the version
  it was made under (see `capture/labeling-sop.md`).
- Datasets with only aggregate quality grades (A/B/C…) are kept on a separate
  grade axis, not force-mapped onto defect classes.
