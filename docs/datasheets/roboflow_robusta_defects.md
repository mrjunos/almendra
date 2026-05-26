# Datasheet — `roboflow_robusta_defects`

**Robusta Coffee Bean Defects** (Roboflow Universe) ·
<https://universe.roboflow.com/coffee-beans-ixp8d/robusta-coffee-bean-defects-hatuw>

- **Licence:** CC BY 4.0 · **Commercial use:** yes · **Status:** usable (Phase 1 baseline)
- **Species:** Robusta · **Roast:** green · **Capture:** controlled · **Format:** COCO instance segmentation
- Adapter: [`../../data/sources/roboflow_robusta_defects.yaml`](../../data/sources/roboflow_robusta_defects.yaml)

## Motivation
The primary source of real *per-class* green-coffee defect labels with a clear,
commercially-usable licence. Brings the pipeline up end-to-end before
proprietary Arabica data exists.

## Composition (as ingested into the catalog)
1507 single-bean crops across 7 canonical classes:

| primary class | beans |
|---|---|
| sound | 463 |
| severe_insect_damage | 349 |
| immature | 229 |
| defect_unspecified | 164 |
| full_black | 158 |
| broken_chipped_cut | 86 |
| hull_husk | 58 |

Split: train 1320 / val 125 / test 62.

## Collection & preprocessing
Polygon/box instances are cropped to one bean per image (12% bbox padding) by
`almendra.datasets.ingest`, then imported into the catalog (`almendra db
migrate`) under one public lot, each defect labelled `label_source=dataset`.

Source label → canonical mapping (`class_map` in the adapter):

| source label | canonical | note |
|---|---|---|
| Good bean | sound | |
| Black | full_black | |
| Broken | broken_chipped_cut | |
| Insect damage | severe_insect_damage | |
| Quaker | immature | quaker = immature bean |
| Empty | hull_husk | **lossy/questionable** |
| Scorched | defect_unspecified | **lossy** — no clean SCA class |

## Curation findings (`almendra db curate`)
- **196 near-duplicate beans** (pHash Hamming ≤ 4) flagged `is_good=false` and
  excluded from export — leaving **1311** good beans. Roboflow exports often
  contain augmented/duplicated frames.
- **222 defect labels down-weighted** for the two lossy mappings:
  `defect_unspecified` (←Scorched) → trust 0.2; `hull_husk` (←Empty) → trust 0.3.
  Use `db export-manifest --min-trust` to drop or de-emphasise them.

## Uses & limitations
- **Robusta, not Arabica** — the target crop is Colombian Arabica. Defect
  morphology largely transfers, but this is a documented domain gap.
- `defect_unspecified` is a catch-all, excluded from per-class defect metrics.

## Licence & distribution
CC BY 4.0. almendra never redistributes the dataset; it is downloaded from
Roboflow under the user's own API key (`ROBOFLOW_API_KEY`).
