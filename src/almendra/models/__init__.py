"""Model architectures.

The backbone is swappable via ``configs/model/*.yaml`` so retraining with a new
architecture needs no code change.

Planned modules
---------------
  backbone.py    shared lightweight backbone registry (torchvision + timm)
  fusion.py      multi-view fusion heads: attention | mean | max
  classifier.py  MultiViewClassifier — backbone -> fusion -> defect head
"""
