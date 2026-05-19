# Rig A — Bill of Materials

Indicative components for the **data-collection rig** (`capture/protocol.md`).
This is a starting specification, not a finalised parts list — quantities and
exact models are refined in Phase 3. Prices are rough ranges for planning only.

## Imaging

| Item | Spec / why | Qty |
|------|-----------|-----|
| Machine-vision camera | **Global shutter** (no motion skew), ≥ 5 MP, C-mount, USB3/GigE | 3+ |
| Lens | Fixed focal length, low distortion, matched to working distance | 1 per camera |
| UV-capable / UV-pass consideration | At least one camera path able to image UV-excited fluorescence (often fine on a standard sensor; verify) | — |

> A 3-camera ring around the bean axis is the minimum for good surface coverage;
> more cameras reduce the number of stage orientations needed.

## Illumination

| Item | Spec / why | Qty |
|------|-----------|-----|
| White LED ring | High-CRI, diffused, **strobable** (synchronised to camera trigger) | 1 |
| UV LED array | 365–395 nm, strobable — excites fluorescence in sour/fungal beans | 1 |
| Backlight panel | Diffuse, even, mounted below the stage for transillumination | 1 |
| Strobe controller | Drives each light briefly + in sync with the camera trigger | 1 |

## Mechanics

| Item | Spec / why | Qty |
|------|-----------|-----|
| Matte-black enclosure | Blocks ambient light; UV-safe when closed | 1 |
| Vibratory feeder | Singulates beans — one bean to the nest at a time | 1 |
| Rotation stage | Re-orients each bean between capture rounds (stepper-driven) | 1 |
| Bean nest | Neutral-coloured, repeatable seating; non-fluorescent under UV | 1 |

## Calibration

| Item | Spec / why | Qty |
|------|-----------|-----|
| Colour target | X-Rite / ColorChecker — white balance + colour constancy | 1 |
| Geometric target | Checkerboard / dot grid — per-camera geometry | 1 |

## Compute & control

| Item | Spec / why | Qty |
|------|-----------|-----|
| Capture PC | Triggers cameras + strobes, writes images + metadata | 1 |
| Microcontroller | Camera/strobe sync + stepper control (e.g. for the trigger bus) | 1 |

## Notes
- **Strobe + global shutter** together freeze the bean — this is what later lets
  Rig B (production) image fast-moving beans without blur.
- Keep the bean nest and enclosure interior **non-fluorescent**, or UV frames
  pick up the rig instead of the bean.
- Mains-powered throughout — no battery/thermal budget (see the project plan).
