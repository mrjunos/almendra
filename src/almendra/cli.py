"""Command-line interface for almendra.

Subcommands
-----------
  info     print the canonical taxonomy and project status
  ingest   build the dataset manifest from downloaded data
  train    train the defect classifier
  eval     evaluate a checkpoint
  export   export a checkpoint to ONNX (+ INT8)
  bench    benchmark inference latency / throughput
  sweep    train + eval + export + bench across backbones (RQ3/RQ4)
  tray-check  segment beans from gridded-tray photos (capture data prep)

The pipeline subcommands accept Hydra-style ``key=value`` overrides, e.g.
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

    evaluate.run(
        _compose(args.overrides),
        checkpoint=args.checkpoint,
        split=args.split,
        views=args.views,
    )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from almendra.export import exporter

    exporter.run(_compose(args.overrides), checkpoint=args.checkpoint)
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    from almendra.bench import latency

    latency.run(_compose(args.overrides), model_path=args.model)
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    from almendra.bench import sweep

    backbones = [name.strip() for name in args.backbones.split(",") if name.strip()]
    sweep.run(
        _compose(args.overrides),
        backbones=backbones,
        epochs=args.epochs,
        out_root=args.out,
    )
    return 0


def cmd_tray_check(args: argparse.Namespace) -> int:
    """Segment beans from gridded-tray photos and write crops + a debug overlay."""
    from pathlib import Path

    from almendra.datasets import tray

    spec = tray.TraySpec(
        rows=args.rows,
        cols=args.cols,
        flip=args.flip,
        marker_dict=args.marker_dict,
        margin_frac=args.margin_frac,
        well_frac=args.well_frac,
    )
    out_dir = Path(args.out)
    crops_dir = out_dir / "crops"

    rect_a = tray.rectify(tray.load_image(args.side_a), spec)
    beans_a = tray.extract_from_rectified(rect_a, spec)
    tray.save_image(tray.draw_overlay(rect_a, spec, beans_a), out_dir / "overlay_a.png")
    print(f"side A: {len(beans_a)} beans found across {spec.rows}x{spec.cols} wells")

    if args.side_b:
        rect_b = tray.rectify(tray.load_image(args.side_b), spec)
        beans_b = tray.extract_from_rectified(rect_b, spec)
        tray.save_image(tray.draw_overlay(rect_b, spec, beans_b), out_dir / "overlay_b.png")
        print(f"side B: {len(beans_b)} beans found")

        paired = tray.pair_sides(beans_a, beans_b, spec)
        two_view = sum(1 for views in paired.values() if len(views) == 2)
        print(f"paired: {two_view} two-view beans, {len(paired) - two_view} single-view")
        for (row, col), views in paired.items():
            for i, crop in enumerate(views):
                tray.save_image(crop, crops_dir / f"bean_r{row}c{col}_v{i}.png")
    else:
        for (row, col), crop in beans_a.items():
            tray.save_image(crop, crops_dir / f"bean_r{row}c{col}.png")

    print(f"crops + overlays written to {out_dir}/")
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
    p_eval.add_argument(
        "--views", type=int, help="evaluate at this view count (overrides the config)"
    )
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

    p_sweep = sub.add_parser("sweep", help="train + eval + export + bench across backbones")
    p_sweep.add_argument(
        "--backbones",
        required=True,
        help="comma-separated backbones (e.g. mobilenet_v3_small,efficientnet_b0)",
    )
    p_sweep.add_argument("--epochs", type=int, default=20, help="epochs per backbone")
    p_sweep.add_argument("--out", default="outputs/sweep", help="output root directory")
    p_sweep.add_argument("overrides", nargs="*", help="Hydra overrides (key=value)")
    p_sweep.set_defaults(func=cmd_sweep)

    p_tray = sub.add_parser("tray-check", help="segment beans from gridded-tray photos")
    p_tray.add_argument("--rows", type=int, required=True, help="number of well rows")
    p_tray.add_argument("--cols", type=int, required=True, help="number of well columns")
    p_tray.add_argument("--side-a", required=True, help="side-A tray photo")
    p_tray.add_argument("--side-b", help="side-B tray photo (optional — enables pairing)")
    p_tray.add_argument("--out", default="outputs/tray", help="output directory")
    p_tray.add_argument(
        "--flip",
        default="mirror_cols",
        choices=["identity", "mirror_rows", "mirror_cols"],
        help="how side B maps to side A after the flip",
    )
    p_tray.add_argument("--marker-dict", default="DICT_4X4_50", help="ArUco dictionary")
    p_tray.add_argument(
        "--margin-frac",
        type=float,
        default=0.10,
        help="grid inset from the marker quad (default: 0.10)",
    )
    p_tray.add_argument(
        "--well-frac",
        type=float,
        default=0.85,
        help="well crop window as a fraction of the cell pitch (default: 0.85)",
    )
    p_tray.set_defaults(func=cmd_tray_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
