"""Build the committed mini-dataset the E2E test trains on.

Samples a handful of *real* crops per class out of the local
``data/processed/`` (DVC-managed, git-ignored) and copies them — downscaled —
into ``tests/e2e/fixtures/processed/`` together with a small ``manifest.jsonl``.
That fixture IS committed, so the E2E gate runs in CI without DVC.

Run from the repo root after the dataset is present locally::

    uv run python -m tests.e2e.build_fixture

Re-running is idempotent: it wipes and rebuilds the fixture tree.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

from almendra.datasets.manifest import BeanRecord, read_manifest, write_manifest
from almendra.paths import processed_dir

# Distinct, well-populated classes: one sound + three defects. Keep the count
# tiny — this whole tree is committed to git.
CLASSES = ["sound", "full_black", "severe_insect_damage", "immature"]
# Per class: enough that train/val/test are all non-empty (loop._build_loaders
# requires train+val; evaluate uses test).
SPLITS = ["train", "train", "train", "val", "test"]
THUMB_PX = 96

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PROCESSED = FIXTURE_DIR / "processed"
FIXTURE_MANIFEST = FIXTURE_PROCESSED / "manifest.jsonl"


def build() -> Path:
    src_processed = processed_dir()
    src_manifest = src_processed / "manifest.jsonl"
    if not src_manifest.is_file():
        raise SystemExit(
            f"{src_manifest} not found — pull the dataset (DVC) before building the fixture."
        )

    records = read_manifest(src_manifest)
    by_class: dict[str, list[BeanRecord]] = {}
    for rec in records:
        by_class.setdefault(rec.defect_class, []).append(rec)

    if FIXTURE_PROCESSED.exists():
        shutil.rmtree(FIXTURE_PROCESSED)

    out_records: list[BeanRecord] = []
    for cls in CLASSES:
        pool = sorted(by_class.get(cls, []), key=lambda r: r.bean_id)
        if len(pool) < len(SPLITS):
            raise SystemExit(f"class {cls!r} has only {len(pool)} crops; need {len(SPLITS)}")
        # Deterministic, spread across the pool so we don't grab near-duplicates.
        step = max(1, len(pool) // len(SPLITS))
        chosen = [pool[i * step] for i in range(len(SPLITS))]
        for rec, split in zip(chosen, SPLITS, strict=True):
            rel = Path(rec.views[0])  # path relative to the processed root
            src_img = src_processed / rel
            dst_img = FIXTURE_PROCESSED / rel
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src_img) as im:
                im.convert("RGB").resize((THUMB_PX, THUMB_PX)).save(dst_img)
            out_records.append(
                BeanRecord(
                    bean_id=rec.bean_id,
                    source=rec.source,
                    defect_class=rec.defect_class,
                    defect_index=rec.defect_index,  # canonical taxonomy index — keep as-is
                    split=split,
                    views=[str(rel)],
                    morphology=rec.morphology,
                    source_image=rec.source_image,
                )
            )

    write_manifest(out_records, FIXTURE_MANIFEST)
    print(f"wrote {len(out_records)} records -> {FIXTURE_MANIFEST}")
    for split in ("train", "val", "test"):
        n = sum(1 for r in out_records if r.split == split)
        print(f"  {split}: {n}")
    return FIXTURE_MANIFEST


if __name__ == "__main__":
    build()
