# Datasheet — `usk_coffee`

**USK-COFFEE: Multi-Class Green Arabica Coffee Bean Dataset** ·
<https://comvis.unsyiah.ac.id/usk-coffee/>

- **Licence:** Public Domain · **Commercial use:** yes · **Status:** usable (not yet ingested)
- **Species:** Arabica · **Roast:** green · **Capture:** controlled · **Format:** classification (one bean per image)
- Adapter: [`../../data/sources/usk_coffee.yaml`](../../data/sources/usk_coffee.yaml)

## Motivation
The only sizeable cleanly-licensed **green-Arabica** set located. Anchors Arabica
appearance and the morphology axis in a Robusta-heavy public pool.

## Composition
~8000 single-bean images. Labels mix a coarse defect split with morphology and
map onto **both** almendra axes:

| source label | defect | morphology |
|---|---|---|
| premium | sound | normal |
| defect | defect_unspecified | normal |
| longberry | sound | longberry |
| peaberry | sound | peaberry |

## Uses & limitations
- **Coarse defect labels** — only `premium` vs `defect`; the `defect` bucket maps
  to the `defect_unspecified` catch-all, so it should be ingested at **low
  trust** and is weak for per-class defect training.
- Valuable mostly for Arabica appearance + the morphology axis.

## Status
Not yet ingested. Requires the `classification` ingester (Step 3) and a
download from the project portal (host occasionally times out).
