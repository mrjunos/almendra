# Physical Capture Protocol — Rig A (Batch Tray Capture)

Standard operating procedure for collecting proprietary green coffee bean images
for almendra. **Rig A** is the data-collection rig — optimised for *coverage and
quality*. Beans are captured in **batches** on a gridded tray, then segmented and
paired automatically by `src/almendra/datasets/tray.py`.

> **Rig A vs Rig B.** Rig A (this document) collects training data: a tray of
> beans, both sides, automatically cropped into paired per-bean views. **Rig B**
> is the high-throughput production capture used by the sorting machine
> (specified in Phase 6). The model trained on Rig A data also runs on Rig B's
> view set — *view-dropout* training makes it view-count agnostic.

## Why a gridded tray

Photographing beans one at a time is the bottleneck. Instead, lay ~50–100 beans
one-per-well in a tray, photograph the whole tray, flip it, photograph again. The
**well address `(row, col)` is each bean's identity**, so a bean's two views are
paired by arithmetic — no per-bean handling, no manual boxes. See
[ADR-0005](../docs/adr/0005-tray-batch-capture.md).

A defect hidden on one face is caught on the other; multi-spectral illumination
catches what plain white light misses:

| Mode | Light | Reveals |
|------|-------|---------|
| Front-light | White LED | Surface colour, texture, shape |
| Back-light | Diffuse transillumination | Internal voids, cracks, insect tunnels, density |
| UV fluorescence | 365–395 nm UV | Sour / fermented / fungal beans (they fluoresce) |

## The tray

```
            [ camera, fixed above ]
                     |
        +------------+------------+
        | #                     # |   # = ArUco marker at each corner
        |    o  o  o  o  o  o      |   o = one bean per well
        |    o  o  o  o  o  o      |
        |    o  o  o  o  o  o      |
        | #                     # |
        +-------------------------+
   matte, NON-green background (blue/magenta); shallow wells on a grid

   photograph side A  ->  sandwich with a 2nd tray + flip  ->  photograph side B
```

`views_per_bean = sides x illumination_modes` (e.g. 2 sides x 3 modes = 6).

---

## Procedure

### Step 0 — Safety & environment
- Dust-free area; coffee chaff scatters light and contaminates samples.
- **UV safety:** never look at the UV source; keep the enclosure closed during UV
  exposure; use UV-blocking eyewear when servicing the rig.
- Let cameras and LEDs reach thermal steady state (~10 min) before a session.

### Step 1 — Build & calibrate the tray (one-time)
1. **Tray** — a rigid tray with a grid of shallow wells (one bean per well),
   a matte **non-green** surface (blue or magenta — far from coffee's colour),
   and four ArUco markers at the corners (`DICT_4X4_50`, IDs 0/1/2/3 =
   TL/TR/BR/BL). A second identical tray is the flip lid. See `capture/bom.md`.
2. **Flip calibration** — determine, once, how side B maps to side A:
   - Place one distinctively marked bean in well `(0, 0)`; fill a few other wells.
   - Run the full capture + flip, then `almendra tray-check`.
   - See which side-B well the marked bean lands in → set `flip` to `identity`,
     `mirror_rows`, or `mirror_cols`. Record it; it never changes for this rig.
3. Record the tray spec (`rows`, `cols`, `flip`, marker dictionary).

### Step 2 — Sampling
1. Draw a representative sample per SCA practice: a **350 g** portion of a
   well-mixed lot.
2. Record provenance: `farm`, `lot_id`, `varietal`, `process`
   (washed/natural/honey), `altitude_m`, `harvest_date`, `moisture_pct`.

### Step 3 — Load the tray
1. Place beans one per well — pour and agitate so they settle singly, or place by
   hand for a research rig.
2. Beans must **not** touch the well rim heavily or each other; empty wells are
   fine (the segmenter skips them).
3. Note any well deliberately left for a known reference bean.

### Step 4 — Session calibration (every session)
1. **White balance & exposure:** shoot the ColorChecker target under white light;
   lock both for the session.
2. Keep one ColorChecker frame per session for later colour-constancy correction.
3. Capture a blank-tray frame under back-light and under UV — flat-field
   references for normalisation.

### Step 5 — Capture side A
For the loaded tray, photograph the **whole tray** once per illumination mode:
white, back-light, UV. Keep the camera fixed and the four markers in frame.

### Step 6 — Flip → capture side B
1. Lay the second (lid) tray face-to-face on the loaded tray; align and clamp.
2. Invert the sandwich about the **calibrated flip axis**; remove the now-top
   tray. Every bean is in its mirrored well, other side up.
3. Photograph side B once per illumination mode, exactly as Step 5.

### Step 7 — Auto-segmentation
Run the segmenter and **inspect the overlay** before trusting a session:

```bash
almendra tray-check --rows R --cols C --flip <calibrated> \
  --side-a side_a_white.jpg --side-b side_b_white.jpg --out outputs/tray
```

Check `overlay_a.png` / `overlay_b.png`: every occupied well boxed green, empty
wells red. If wells are mis-located, re-shoot with all four markers clearly in
frame. The tool writes paired per-bean crops to `outputs/tray/crops/`.

### Step 8 — Labelling
Label each bean **by its well address** against the SCA reference — see
`capture/labeling-sop.md`. Labelling is blind to model predictions.

### Step 9 — QA & ingestion
1. **Markers:** all four detected in every photo (the overlay confirms this).
2. **Coverage:** occupied-well count matches the number of beans loaded.
3. **Quality:** reject blurred or clipped frames; log rejects, never silently drop.
4. **Ingest:** register the session into DVC with the current `taxonomy.yaml`
   `schema_version`; add an entry under `docs/datasheets/`.

---

## Folder & metadata schema
Target layout under `data/raw/proprietary_tray/sessions/<session_id>/`:

```
<session_id>/
  session.json                  # provenance, tray spec, calibration references
  side_a_white.jpg   side_b_white.jpg
  side_a_backlight.jpg   side_b_backlight.jpg
  side_a_uv.jpg   side_b_uv.jpg
  labels.csv                    # row,col,defect_class,morphology  (from Step 8)
```

v1 pairs the white-light `side_a`/`side_b` into two-view beans; back-light and UV
are captured now and folded in as the ingester gains multi-spectral pairing.

## Targets & cadence
- **v1 target:** ≥ 200 beans **per defect class** (balanced); deliberately source
  the rare Category 1 defects rather than waiting for them to appear.
- After each session, check per-class counts and bias the next sample's sourcing
  toward under-represented classes.

## Versioning this protocol
Any change to the tray geometry, illumination, flip axis, or folder schema is a
new **protocol version**. Record it in `docs/research-log.md` and stamp each
session with the version, so data from different rigs stays distinguishable.
