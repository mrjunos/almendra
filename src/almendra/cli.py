"""Command-line interface for almendra.

Subcommands
-----------
  info     print the canonical taxonomy and project status
  ingest   build the dataset manifest from downloaded data
  train    train the defect classifier
  eval     evaluate a checkpoint
  export   export a checkpoint to ONNX (+ INT8)
  bench    benchmark inference latency / throughput

All pipeline subcommands accept Hydra-style ``key=value`` overrides, e.g.
``almendra train model=efficientnet_b0 train.epochs=50``.
"""

from __future__ import annotations

import argparse
import sys

from almendra import __version__
from almendra.taxonomy import get_taxonomy


def _compose(overrides: list[str] | None):
    """Compose the Hydra config (configs/config.yaml) with CLI overrides."""
    from hydra import compose, initialize_config_dir
    from hydra.core.global_hydra import GlobalHydra

    from almendra.paths import configs_dir

    GlobalHydra.instance().clear()
    with initialize_config_dir(version_base=None, config_dir=str(configs_dir())):
        return compose(config_name="config", overrides=list(overrides or []))


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


def cmd_ingest(args: argparse.Namespace) -> int:
    from almendra.datasets import ingest

    ingest.run(_compose(args.overrides))
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    from almendra.train import loop

    loop.run(_compose(args.overrides))
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    from almendra.eval import evaluate

    evaluate.run(_compose(args.overrides), checkpoint=args.checkpoint, split=args.split)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from almendra.export import exporter

    exporter.run(_compose(args.overrides), checkpoint=args.checkpoint)
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    from almendra.bench import latency

    latency.run(_compose(args.overrides), model_path=args.model)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="almendra",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"almendra {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="print the taxonomy and project status")
    p_info.set_defaults(func=cmd_info)

    p_ingest = sub.add_parser("ingest", help="build the dataset manifest")
    p_ingest.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_ingest.set_defaults(func=cmd_ingest)

    p_train = sub.add_parser("train", help="train the defect classifier")
    p_train.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_train.set_defaults(func=cmd_train)

    p_eval = sub.add_parser("eval", help="evaluate a checkpoint")
    p_eval.add_argument("--checkpoint", help="path to a checkpoint (.pt)")
    p_eval.add_argument("--split", default="test", help="dataset split (default: test)")
    p_eval.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_eval.set_defaults(func=cmd_eval)

    p_export = sub.add_parser("export", help="export a checkpoint to ONNX (+ INT8)")
    p_export.add_argument("--checkpoint", help="path to a checkpoint (.pt)")
    p_export.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_export.set_defaults(func=cmd_export)

    p_bench = sub.add_parser("bench", help="benchmark inference latency")
    p_bench.add_argument("--model", help="path to an ONNX model")
    p_bench.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_bench.set_defaults(func=cmd_bench)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
