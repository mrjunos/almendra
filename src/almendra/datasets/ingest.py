"""Ingest downloaded datasets into a unified single-bean manifest.

Reads the source adapters in ``data/sources/``, crops detection/segmentation
instances to single-bean images under ``data/processed/``, maps source labels to
the canonical taxonomy, and writes ``data/processed/manifest.jsonl``.

Phase 1 implements the COCO instance ingester (Roboflow exports). Classification
sources and stratified-split sources are added with USK-COFFEE (Phase 1+).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from PIL import Image

from almendra.datasets.manifest import (
    BeanRecord,
    class_distribution,
    write_manifest,
)
from almendra.paths import processed_dir, raw_dir, sources_dir
from almendra.taxonomy import Taxonomy, get_taxonomy

# Fraction of the bbox size added as padding on each side when cropping a bean.
_BBOX_PADDING = 0.12

# Roboflow COCO exports use these split sub-directories.
_COCO_SPLIT_DIRS = {"train": "train", "valid": "val", "test": "test"}


def load_source(name: str) -> dict:
    """Load a dataset adapter from ``data/sources/<name>.yaml``."""
    with (sources_dir() / f"{name}.yaml").open() as fh:
        return yaml.safe_load(fh)


def _crop_bbox(image: Image.Image, bbox: list[float]) -> Image.Image:
    """Crop a padded COCO bbox ([x, y, w, h]) from an image."""
    x, y, w, h = bbox
    pad_x, pad_y = w * _BBOX_PADDING, h * _BBOX_PADDING
    left = max(0, round(x - pad_x))
    top = max(0, round(y - pad_y))
    right = min(image.width, round(x + w + pad_x))
    bottom = min(image.height, round(y + h + pad_y))
    return image.crop((left, top, right, bottom))


def _ingest_coco_source(
    name: str, cfg: dict, taxonomy: Taxonomy, out_root: Path
) -> list[BeanRecord]:
    """Ingest a COCO source: crop each instance to a single-bean image."""
    class_map = cfg.get("class_map") or {}
    if not class_map:
        raise ValueError(f"source '{name}' has an empty class_map; cannot ingest")

    src_root = raw_dir() / name
    records: list[BeanRecord] = []
    skipped = 0
    counter = 0

    for src_split, canon_split in _COCO_SPLIT_DIRS.items():
        ann_path = src_root / src_split / "_annotations.coco.json"
        if not ann_path.is_file():
            continue
        coco = json.loads(ann_path.read_text())
        cat_name = {c["id"]: c["name"] for c in coco["categories"]}
        images = {im["id"]: im for im in coco["images"]}

        for ann in coco["annotations"]:
            canon = class_map.get(cat_name.get(ann["category_id"], ""))
            image_info = images.get(ann["image_id"])
            if canon is None or image_info is None:
                skipped += 1
                continue
            img_path = src_root / src_split / image_info["file_name"]
            if not img_path.is_file():
                skipped += 1
                continue

            with Image.open(img_path) as image:
                crop = _crop_bbox(image.convert("RGB"), ann["bbox"])

            bean_id = f"{name}_{counter:06d}"
            counter += 1
            rel_path = Path(name) / canon / f"{bean_id}.png"
            (out_root / rel_path).parent.mkdir(parents=True, exist_ok=True)
            crop.save(out_root / rel_path)

            records.append(
                BeanRecord(
                    bean_id=bean_id,
                    source=name,
                    defect_class=canon,
                    defect_index=taxonomy.index_of(canon),
                    split=canon_split,
                    views=[str(rel_path)],
                    source_image=f"{src_split}/{image_info['file_name']}",
                )
            )

    print(f"  {name}: {len(records)} beans ingested, {skipped} annotations skipped")
    return records


# --- Classification ingester ----------------------------------------------------
# For class-folder datasets (one bean per image, label = directory name). Two
# layouts are supported under ``data/raw/<source>/``:
#   (a) split subdirs:   <split>/<class>/*.png      (split ∈ train|val|valid|test)
#   (b) flat:            <class>/*.png              (split assigned deterministically
#                                                    via a hash of the filename)
# ``class_map`` values can be a plain canonical defect-class string, or a dict
# ``{defect: ..., morphology: ...}`` for sources like USK-COFFEE that label both
# axes from the same directory name.

_IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
# Roboflow exports use "valid" for the validation split; honour both spellings.
_CLASSIFICATION_SPLIT_DIRS = {"train": "train", "val": "val", "valid": "val", "test": "test"}


def _resolve_classification_labels(value) -> dict | None:
    """Normalise a class_map value into ``{'defect': name, 'morphology': name?}``."""
    if value is None:
        return None
    if isinstance(value, str):
        return {"defect": value, "morphology": None}
    if isinstance(value, dict):
        return {"defect": value.get("defect"), "morphology": value.get("morphology")}
    return None


def _hash_split(name: str, splits_cfg: dict) -> str:
    """Deterministic train/val/test pick from a uniform hash of ``name``."""
    import hashlib

    h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:16], 16) / (1 << 64)
    train = float(splits_cfg.get("train", 0.70))
    val = float(splits_cfg.get("val", 0.15))
    if h < train:
        return "train"
    if h < train + val:
        return "val"
    return "test"


def _ingest_classification_source(
    name: str, cfg: dict, taxonomy: Taxonomy, out_root: Path, src_root: Path | None = None
) -> list[BeanRecord]:
    """Ingest a class-folder classification source (see module note above)."""
    class_map = cfg.get("class_map") or {}
    if not class_map:
        raise ValueError(f"source '{name}' has an empty class_map; cannot ingest")

    src_root = Path(src_root) if src_root is not None else raw_dir() / name
    splits_cfg = cfg.get("splits", {"train": 0.70, "val": 0.15, "test": 0.15})

    split_dirs_present = [d for d in _CLASSIFICATION_SPLIT_DIRS if (src_root / d).is_dir()]

    def _iter_split_layout():
        for split_dir in split_dirs_present:
            canon_split = _CLASSIFICATION_SPLIT_DIRS[split_dir]
            for class_dir in sorted((src_root / split_dir).iterdir()):
                if not class_dir.is_dir():
                    continue
                for img in sorted(class_dir.iterdir()):
                    if img.suffix.lower() in _IMAGE_EXTS:
                        yield img, class_dir.name, canon_split

    def _iter_flat_layout():
        for class_dir in sorted(src_root.iterdir()):
            if not class_dir.is_dir() or class_dir.name in _CLASSIFICATION_SPLIT_DIRS:
                continue
            for img in sorted(class_dir.iterdir()):
                if img.suffix.lower() in _IMAGE_EXTS:
                    yield img, class_dir.name, _hash_split(img.name, splits_cfg)

    iterator = _iter_split_layout() if split_dirs_present else _iter_flat_layout()

    records: list[BeanRecord] = []
    skipped = 0
    counter = 0
    for img_path, src_class, split in iterator:
        labels = _resolve_classification_labels(class_map.get(src_class))
        if labels is None or not labels.get("defect"):
            skipped += 1
            continue
        canon = labels["defect"]
        if canon not in taxonomy.defect_classes:
            skipped += 1
            continue

        bean_id = f"{name}_{counter:06d}"
        counter += 1
        rel_path = Path(name) / canon / f"{bean_id}.png"
        dst = out_root / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(img_path) as im:
            im.convert("RGB").save(dst)

        records.append(
            BeanRecord(
                bean_id=bean_id,
                source=name,
                defect_class=canon,
                defect_index=taxonomy.index_of(canon),
                split=split,
                views=[str(rel_path)],
                morphology=labels.get("morphology") or "normal",
                source_image=str(img_path.relative_to(src_root)),
            )
        )

    print(f"  {name}: {len(records)} beans ingested, {skipped} skipped")
    return records


# format string (from the source adapter) -> ingester
_INGESTERS = {
    "instance_segmentation": _ingest_coco_source,
    "detection": _ingest_coco_source,
    "classification": _ingest_classification_source,
}


def run(cfg) -> Path:
    """Ingest every source in ``cfg.data.sources`` into the manifest."""
    taxonomy = get_taxonomy()
    out_root = processed_dir()
    out_root.mkdir(parents=True, exist_ok=True)

    records: list[BeanRecord] = []
    for name in cfg.data.sources:
        source_cfg = load_source(name)
        ingester = _INGESTERS.get(source_cfg.get("format"))
        if ingester is None:
            print(f"  {name}: skipped (no ingester for format '{source_cfg.get('format')}')")
            continue
        if not (raw_dir() / name).is_dir():
            print(f"  {name}: skipped (not downloaded — see scripts/download_public_datasets.py)")
            continue
        records.extend(ingester(name, source_cfg, taxonomy, out_root))

    if not records:
        raise RuntimeError("no data ingested — download a dataset first")

    manifest_path = out_root / "manifest.jsonl"
    write_manifest(records, manifest_path)

    print(f"manifest: {len(records)} beans -> {manifest_path}")
    for cls, count in sorted(class_distribution(records).items(), key=lambda kv: -kv[1]):
        print(f"  {cls:<22} {count}")
    return manifest_path
