# Dataset Datasheets

One datasheet per dataset almendra uses, in the spirit of *Datasheets for
Datasets* (Gebru et al.). almendra **never redistributes datasets** — each is
downloaded from its original host under its own licence; these datasheets record
provenance, licence and how the data is used.

A machine-readable adapter for each dataset lives in
[`../../data/sources/`](../../data/sources/). A full prose datasheet is written
when a dataset is actually ingested.

## Licence & status summary

| Dataset | Species | Licence | Commercial | Status |
|---------|---------|---------|-----------|--------|
| [`roboflow_robusta_defects`](roboflow_robusta_defects.md) | Robusta | CC BY 4.0 | Yes | Usable — Phase 1 baseline (ingested) |
| [`usk_coffee`](usk_coffee.md) | Arabica | Public Domain | Yes | Usable — confirm host reachability |
| [`samruddhk_grading`](samruddhk_grading.md) | Robusta | MIT | Yes | Reference only (grades, not defects) |
| [`mendeley_cbd_robusta`](mendeley_cbd_robusta.md) | Robusta | CC BY 4.0 | Yes | Reference only (grades, not defects) |
| [`kaggle_17defects`](kaggle_17defects.md) | Arabica | Unknown | Unknown | **Blocked** — licence unverified |

## Known limitations of the public pool
- **Robusta-heavy.** Most cleanly-licensed data is Robusta; the target crop is
  Colombian Arabica. Defect morphology largely transfers, but this is a real
  domain gap — the reason proprietary Arabica capture matters.
- **Coarse Arabica labels.** The main Arabica set (`usk_coffee`) only separates
  `defect` vs `premium` on the defect axis.
- **Licence gap.** The richest Arabica defect taxonomy (`kaggle_17defects`) has
  no stated licence and is not used until that is resolved.

## Datasheet template
Each per-dataset datasheet should cover: **Motivation** (why it was created),
**Composition** (counts, classes, capture conditions), **Collection** (how/when),
**Preprocessing** (what almendra does to it — cropping, label mapping),
**Uses & limitations**, and **Licence & distribution**.
