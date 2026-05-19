"""Command-line interface for almendra.

Subcommands
-----------
  info     print the canonical taxonomy and project status   (implemented)
  train    train a model                                     (Phase 1)
  eval     evaluate a checkpoint                              (Phase 1)
  export   export a checkpoint to ONNX (+ INT8)               (Phase 1)
  bench    benchmark inference latency / throughput           (Phase 5)

The planned subcommands are deliberate, honest stubs: the pipeline they drive is
built phase by phase (see docs/research-log.md).
"""

from __future__ import annotations

import argparse
import sys

from almendra import __version__
from almendra.taxonomy import get_taxonomy

# Subcommand name -> phase in which it becomes functional.
_PLANNED = {
    "train": "Phase 1",
    "eval": "Phase 1",
    "export": "Phase 1",
    "bench": "Phase 5",
}


def cmd_info(_args: argparse.Namespace) -> int:
    """Print the canonical taxonomy and a short project status."""
    tax = get_taxonomy()
    status = "verified" if tax.verified else "PROVISIONAL — unverified"
    print(f"almendra v{__version__}")
    print(f"taxonomy schema v{tax.schema_version}  ({status})")
    print(f"reference: {tax.reference}")

    print(f"\ndefect classes ({tax.num_defect_classes}) — model output order:")
    for c in sorted(tax.defect_classes.values(), key=lambda c: c.index):
        flag = "accept" if c.accept else "reject"
        print(f"  [{c.index:>2}] {c.name:<22} {c.category_name:<10} {flag}")

    print(f"\nmorphology classes ({len(tax.morphology_classes)}):")
    for c in sorted(tax.morphology_classes.values(), key=lambda c: c.index):
        print(f"  [{c.index:>2}] {c.name}")
    return 0


def _make_planned(name: str):
    """Build a handler for a not-yet-implemented subcommand."""

    def _run(_args: argparse.Namespace) -> int:
        print(f"`almendra {name}` is not implemented yet ({_PLANNED[name]}).")
        print("Track progress in docs/research-log.md.")
        return 0

    return _run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="almendra",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"almendra {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="print the taxonomy and project status")
    info.set_defaults(func=cmd_info)

    for name, phase in _PLANNED.items():
        p = sub.add_parser(name, help=f"{name} ({phase})")
        p.add_argument("overrides", nargs="*", help="Hydra-style config overrides (key=value)")
        p.set_defaults(func=_make_planned(name))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
