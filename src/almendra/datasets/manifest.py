"""Dataset manifest — one record per bean, with canonical labels.

`data/processed/manifest.jsonl` is the single index the training pipeline reads.
Each line is one bean: its canonical labels, the image paths of its views, and
its split. Multi-view from the start — `views` is a list, length 1 for the
single-view baseline.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class BeanRecord:
    """One bean: a set of view images plus canonical labels."""

    bean_id: str
    source: str
    defect_class: str
    defect_index: int
    split: str  # train | val | test
    views: list[str]  # image paths relative to the processed root
    morphology: str = "normal"
    source_image: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> BeanRecord:
        return cls(**json.loads(line))


def write_manifest(records: list[BeanRecord], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(record.to_json() + "\n")


def read_manifest(path: str | Path) -> list[BeanRecord]:
    path = Path(path)
    with path.open(encoding="utf-8") as fh:
        return [BeanRecord.from_json(line) for line in fh if line.strip()]


def filter_split(records: list[BeanRecord], split: str) -> list[BeanRecord]:
    return [r for r in records if r.split == split]


def class_distribution(records: list[BeanRecord]) -> dict[str, int]:
    """Count beans per defect class."""
    dist: dict[str, int] = {}
    for record in records:
        dist[record.defect_class] = dist.get(record.defect_class, 0) + 1
    return dist
