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


# format string (from the source adapter) -> ingester
_INGESTERS = {
    "instance_segmentation": _ingest_coco_source,
    "detection": _ingest_coco_source,
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
