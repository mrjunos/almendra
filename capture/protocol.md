# Physical Capture Protocol — Rig A (Data Collection)

This is the standard operating procedure for collecting proprietary green coffee
bean images for almendra. It describes **Rig A**, the data-collection rig:
optimised for *completeness and quality*, not speed.

> **Rig A vs Rig B.** Rig A (this document) collects the richest possible
> training data — every bean, every angle, every spectrum. **Rig B** is the
> high-throughput production capture used by the sorting machine; it is
> specified separately in Phase 6. The model trained on Rig A data is designed
> (via *view-dropout*) to also run on Rig B's smaller view set — "collect rich,
> deploy lean".

## Why multi-view, multi-spectral

A defect on the underside of a bean is invisible to a single top-down photo.
Rig A therefore records each bean from several **angles** under three
**illumination modes**:

| Mode | Light | Reveals |
|------|-------|---------|
| Front-light | White LED ring | Surface colour, texture, shape |
| Back-light | Diffuse transillumination panel | Internal voids, cracks, insect tunnels, density (floaters) |
| UV fluorescence | 365–395 nm UV | Sour / fermented / fungal beans (they fluoresce) |

## Rig A layout

```
                  [ white LED ring ]
                         |
   [cam 0] ----.    .----+----.    .---- [cam 2]
                \   |  bean   |   /
                 \  | on the  |  /
                  \ | rotation|/
        [cam 1] ----| stage   |
                    +---------+
                  [ UV LED array ]
                  [ backlight panel ] (below, shines up through the stage)

   Everything inside a matte-black enclosure. See capture/bom.md.
```

`views_per_bean = n_orientations x n_cameras x n_spectra` (e.g. 4 x 3 x 3 = 36).

---

## Procedure

### Step 0 — Safety & environment
- Work in a dust-free area; coffee chaff scatters light and contaminates samples.
- **UV safety:** never look at the UV array directly; the enclosure must be
  closed during UV strobes. Use UV-blocking eyewear when servicing the rig.
- Let cameras and LEDs reach thermal steady state (~10 min) before a session.

### Step 1 — Sampling
1. Draw a representative sample following SCA practice: a **350 g** portion from
   a well-mixed lot.
2. Record provenance for the whole sample:
   - `farm`, `lot_id`, `varietal`, `process` (washed / natural / honey),
     `altitude_m`, `harvest_date`, `moisture_pct` (if measured).
3. Assign a `lot_id` — all beans from this draw share it.

### Step 2 — Rig calibration (every session)
1. **White balance & exposure:** capture the ColorChecker target under the white
   ring; lock white balance and exposure for the session.
2. **Colour reference:** keep one ColorChecker shot per session for later
   colour-constancy correction.
3. **Geometry:** capture the calibration grid so per-camera angles are known.
4. **UV & backlight:** capture a blank-stage frame under each — these are the
   flat-field references for normalisation.
5. Write all of the above into the session metadata (Step 5).

### Step 3 — Singulation & loading
1. Feed beans from the vibratory feeder so exactly **one bean** reaches the nest.
2. Seat the bean on the rotation stage. Reject overlapping/touching beans back to
   the feeder.

### Step 4 — Capture sequence (per bean)
For each bean, assign a unique `bean_id`, then:

```
for orientation in 0 .. n_orientations-1:        # rotation stage steps
    rotate stage to orientation
    for spectrum in [white, backlight, uv]:
        fire the strobe for `spectrum`
        trigger ALL cameras simultaneously (global shutter)
        save one image per camera
```

- Strobes are **short** (freeze any residual motion) and **synchronised** to the
  camera trigger.
- Only one illumination mode is on per capture — never mix.
- After the last orientation, eject the bean to the **graded tray** for Step 6.

### Step 5 — File & metadata schema
Store under `data/raw/proprietary/<lot_id>/`:

```
<lot_id>/
  session.json                       # provenance + calibration references
  bean_000123/
    view_a0_c0_white.png
    view_a0_c0_backlight.png
    view_a0_c0_uv.png
    view_a0_c1_white.png
    ...
    bean.json                        # bean_id, orientation map, capture timestamps
```

`bean.json` records: `bean_id`, `lot_id`, list of views with
`(orientation, camera, spectrum)`, and capture timestamps. **No label yet** —
labelling is a separate, blind step (see `capture/labeling-sop.md`).

### Step 6 — Labelling
Hand the graded tray to a trained grader. Follow `capture/labeling-sop.md`.
Labelling is done **without** seeing model predictions, against the SCA defect
reference chart.

### Step 7 — Session QA & ingestion
1. **Completeness:** every `bean_id` has the expected number of views.
2. **Quality:** reject blurred, clipped (over/under-exposed) or empty frames; log
   rejects, do not silently drop them.
3. **Schema:** validate `session.json` / `bean.json` against the schema.
4. **Ingest:** register the lot into DVC with the current `data/taxonomy.yaml`
   `schema_version`; add a dataset entry under `docs/datasheets/`.

---

## Targets & cadence
- **v1 target:** ≥ 200 beans **per defect class** (balanced), prioritising the
  rare Category 1 defects — collect those deliberately, do not wait for them to
  appear by chance.
- Re-balance: after each lot, check per-class counts and bias the next sample's
  sourcing toward under-represented classes.

## Versioning this protocol
Any change to camera count, angles, illumination, or the file schema is a new
**protocol version**. Record it in `docs/research-log.md` and stamp captured
sessions with the protocol version, so data collected under different rigs stays
distinguishable during training.
