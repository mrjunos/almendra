# Labelling SOP

How a captured bean gets its ground-truth label. Label quality caps model
quality — this step is treated as rigorously as the model code.

## Principles
- **Blind:** label against the bean and the SCA reference only — never against
  model predictions.
- **Physical first:** the grader labels the *physical bean* in its tray well
  (Step 8 of the capture protocol), using the captured images as support.
- **One axis at a time:** assign a `defect` class and, separately, a
  `morphology` class — see `data/taxonomy.yaml`.

## Who
A grader trained on the **SCA Arabica Green Coffee Defect Handbook**. For v1 this
may be the project lead; the SOP is written so a second grader can be added.

## Procedure (per bean)
1. Locate the bean by its well address `(row, col)` in the capture tray.
2. Inspect it against the SCA reference defect chart; consult the captured
   front-light, back-light and UV images for hidden damage.
3. Assign exactly **one** `defect` class from `data/taxonomy.yaml`.
   - If defective but the type is unclear, use `defect_unspecified` — do **not**
     guess a specific defect.
4. Assign exactly **one** `morphology` class (`normal` unless clearly otherwise).
5. Record: well `(row, col)`, `defect`, `morphology`, `grader_id`,
   `taxonomy_version`, `timestamp`, and free-text `notes` for anything ambiguous.

## Inter-annotator agreement (IAA)
- A **random ≥ 10 %** of every lot is **independently double-labelled**.
- Report **Cohen's κ** per lot in `docs/research-log.md`.
- κ < 0.8 on the defect axis triggers a taxonomy/training review before the lot
  is used — ambiguous classes get clearer reference images or get merged.

## Disagreement resolution
1. Two graders disagree → a third adjudicates, or both re-examine together.
2. If still unresolved, label `defect_unspecified` and log it as a taxonomy gap.
3. Recurring disagreements are taxonomy bugs — fix `data/taxonomy.yaml`, bump its
   `schema_version`, and open an ADR.

## Versioning
Every label row stores the `taxonomy_version` it was made under. When the
taxonomy changes, affected lots are re-labelled or explicitly marked stale —
labels and schema never drift apart silently.
