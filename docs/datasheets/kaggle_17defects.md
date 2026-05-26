# Datasheet — `kaggle_17defects`

**Coffee Green Bean with 17 Defects (Original)** (Kaggle) ·
<https://www.kaggle.com/datasets/sujitraarw/coffee-green-bean-with-17-defects-original>

- **Licence:** unknown · **Commercial use:** unknown · **Status:** 🔴 **BLOCKED — licence unverified**
- **Species:** Arabica · **Roast:** green · **Format:** classification (~6850 images)
- Adapter: [`../../data/sources/kaggle_17defects.yaml`](../../data/sources/kaggle_17defects.yaml)

## Motivation
Potentially the **richest Arabica defect taxonomy** in the public pool — 17
defect classes, closely aligned to the SCA handbook almendra targets.

## Why it is blocked
The dataset page states **no licence**. almendra does not ingest data without a
clear, compatible licence, so this source is gated:

- The adapter's `class_map` is intentionally **empty** → the ingester refuses it.
- `db audit` flags it under "license-blocked sources holding beans" if anything
  is ever imported.

## To unblock
1. Confirm the licence with the uploader / Kaggle (need explicit terms allowing
   research + the project's use).
2. If cleared: inspect and record the 17 label strings, fill the `class_map`,
   set `status: usable`, and document the mapping here.

Until then: **do not download or ingest.**
