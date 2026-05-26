# Datasheet — `samruddhk_grading`

**Coffee Bean Grading Dataset** (Hugging Face) ·
<https://huggingface.co/datasets/SamruddhK/coffee-bean-grading-dataset>

- **Licence:** MIT · **Commercial use:** yes · **Status:** reference only
- **Species:** Robusta · **Roast:** green · **Capture:** controlled lightbox · **Format:** instance segmentation (~3877 images)
- Adapter: [`../../data/sources/samruddhk_grading.yaml`](../../data/sources/samruddhk_grading.yaml)

## Motivation
Clean, MIT-licensed, lightbox polygon masks — **excellent for validating the
crop-to-single-bean pipeline**.

## Composition
Grades A/B/C/D — aggregate quality bands, **not per-bean defect types**.

## Uses & limitations
- **Not a defect source** (lossy: grades don't map to defect classes), so it is
  `reference_only` and kept off the defect axis.
- Best use is pipeline validation (segmentation → single-bean crops).

## Status
Not ingested onto the defect axis. Useful later as a clean test of the
`instance_segmentation` crop path.
