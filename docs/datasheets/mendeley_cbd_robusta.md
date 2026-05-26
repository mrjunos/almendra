# Datasheet — `mendeley_cbd_robusta`

**Coffee Beans Dataset (CBD) — Robusta** (Mendeley Data) ·
<https://data.mendeley.com/datasets/52877z55vr/1>

- **Licence:** CC BY 4.0 · **Commercial use:** yes · **Status:** reference only
- **Species:** Robusta · **Roast:** green · **Capture:** controlled lightbox · **Format:** classification (~450 images)
- Adapter: [`../../data/sources/mendeley_cbd_robusta.yaml`](../../data/sources/mendeley_cbd_robusta.yaml)

## Motivation
Small, high-quality controlled-lighting set. Used as a **grade-axis reference**
and to stress-test the multi-bean `detect_then_crop` ingestion path.

## Composition
9 industrial **grades** (A/AA/AAA/AB/C, PB-I/PB-II peaberry, BITS, BULK) — these
are aggregate quality bands, **not per-bean defect types**.

## Uses & limitations
- **Not a defect source.** Grades do not decompose into SCA defect classes
  (lossy), so it is `reference_only` and excluded from the defect axis.
- PB-* grades do inform the **morphology** axis (peaberry).

## Status
Not ingested onto the defect axis. Multiple beans per lightbox image → needs the
`detect_then_crop` ingester (Step 3).
