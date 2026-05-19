# Rig A — Bill of Materials

Indicative components for the **batch tray capture rig** (`capture/protocol.md`).
A starting specification, not a finalised parts list — refined in Phase 3.

## The tray

| Item | Spec / why | Qty |
|------|-----------|-----|
| Gridded well-tray | Rigid; a grid of shallow wells, one bean per well; matte **non-green** surface (blue/magenta). 3D-printed or laser-cut. | 2 |
| ArUco markers | Printed `DICT_4X4_50`, IDs 0–3, one per corner, with a white quiet zone. Enable rectification of any (even handheld) photo. | 4 per tray |

> Two identical trays: one holds the beans, the second is the face-to-face lid
> used for the flip (Step 6). Conical/funnel wells help beans settle singly and
> survive the flip.

## Imaging

| Item | Spec / why | Qty |
|------|-----------|-----|
| Camera | A single fixed camera above the tray is enough — the markers rectify perspective. A global-shutter machine-vision camera is ideal; a decent fixed phone/DSLR also works. | 1 |
| Lens | Fixed focal length, low distortion, the whole tray + 4 markers in frame | 1 |
| Mounting | Rigid copy-stand / arm so the tray-to-camera geometry is repeatable | 1 |

## Illumination

| Item | Spec / why | Qty |
|------|-----------|-----|
| White LED panel | High-CRI, diffuse, even across the whole tray | 1 |
| UV LED array | 365–395 nm — excites fluorescence in sour/fungal beans | 1 |
| Backlight panel | Diffuse, even, behind/under the tray for transillumination | 1 |

## Enclosure & calibration

| Item | Spec / why | Qty |
|------|-----------|-----|
| Matte-black enclosure | Blocks ambient light; UV-safe when closed | 1 |
| Colour target | X-Rite / ColorChecker — white balance + colour constancy | 1 |

## Compute

| Item | Spec / why | Qty |
|------|-----------|-----|
| Capture PC / laptop | Runs `almendra tray-check` on each session's photos | 1 |

## Notes
- The tray + corner markers replace the per-bean rotation stage and vibratory
  feeder of a singulating rig — ~50–100 beans are captured per pair of photos.
- Keep the tray surface and enclosure **non-fluorescent**, or UV frames pick up
  the rig instead of the beans.
- A *non-green* tray colour is essential — green beans on a green tray do not
  segment. Blue or magenta separate cleanly.
- Mains-powered throughout — no battery/thermal budget (see the project plan).
