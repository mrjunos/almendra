"""Dataset loading and ingestion.

Each *sample* is a set of images of one bean (multiple angles x illumination
spectra) fused into a single per-bean label — see docs/methodology.md.

Planned modules
---------------
  ingest.py      download adapters -> unified single-bean crops + a manifest
  manifest.py    the dataset manifest schema (one row per bean, canonical labels)
  multiview.py   MultiViewBeanDataset — yields a variable-size set of views per bean
  transforms.py  augmentation, including multi-view "view-dropout"
"""
