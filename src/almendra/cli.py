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
  db       manage the centralized bean catalog (init / migrate / export-manifest / audit)
  ui       launch the local Streamlit UI (Phase 6)

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


def cmd_ui(args: argparse.Namespace) -> int:
    """Launch the local Streamlit UI by exec'ing ``streamlit run`` on the app."""
    import os
    from pathlib import Path

    app_path = Path(__file__).parent / "ui" / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(f"UI app not found at {app_path}")
    try:
        import streamlit.web.cli as stcli  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "Streamlit is not installed. Run `uv sync --extra ui` (or "
            "`pip install almendra[ui]`) and try again."
        ) from exc
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(args.port),
        "--server.headless",
        "true" if args.headless else "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    if args.extra:
        sys.argv.extend(args.extra)
    os.environ.setdefault("ALMENDRA_UI_ROOT", str(Path.cwd()))
    return int(stcli.main())


def cmd_db(args: argparse.Namespace) -> int:
    """Centralized catalog: init/seed, migrate the manifest in, export, audit."""
    from almendra.db.audit import print_audit
    from almendra.db.catalog import default_db_path, get_engine, get_session, init_db
    from almendra.db.curate import curate
    from almendra.db.export import export_manifest
    from almendra.db.migrate import migrate_manifest
    from almendra.db.seed import seed_all

    db_path = args.db or default_db_path()
    engine = get_engine(db_path)

    if args.db_command == "init":
        init_db(engine)
        with get_session(engine) as session:
            seed_all(session)
        print(f"catalog initialised + seeded -> {db_path}")
        return 0

    if args.db_command == "migrate":
        init_db(engine)
        with get_session(engine) as session:
            seed_all(session)
            counts = migrate_manifest(session, manifest_path=args.manifest)
        print(
            f"migrated {counts['beans']} beans ({counts['skipped']} already present) -> {db_path}"
        )
        return 0

    if args.db_command == "export-manifest":
        provenance = None if args.all_provenance else ("public_dataset",)
        with get_session(engine) as session:
            out = export_manifest(
                session,
                out_path=args.out,
                good_only=not args.include_not_good,
                provenance_types=provenance,
                min_trust=args.min_trust,
            )
        print(f"manifest exported -> {out}")
        return 0

    if args.db_command == "curate":
        with get_session(engine) as session:
            summary = curate(
                session,
                dedup_threshold=args.dedup_threshold,
                min_px=args.min_px,
                min_stddev=args.min_stddev,
                dry_run=args.dry_run,
            )
        tag = " (dry-run, nothing written)" if args.dry_run else ""
        print(f"curation summary{tag}:")
        for key, value in summary.items():
            print(f"  {key:<22} {value}")
        return 0

    if args.db_command == "audit":
        with get_session(engine) as session:
            print_audit(session)
        return 0

    raise SystemExit(f"unknown db command: {args.db_command}")


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

    p_ui = sub.add_parser("ui", help="launch the local Streamlit UI")
    p_ui.add_argument("--port", type=int, default=8501, help="server port (default: 8501)")
    p_ui.add_argument(
        "--headless",
        action="store_true",
        help="don't auto-open a browser (useful over SSH)",
    )
    p_ui.add_argument("extra", nargs=argparse.REMAINDER, help="extra args forwarded to streamlit")
    p_ui.set_defaults(func=cmd_ui)

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

    p_db = sub.add_parser("db", help="manage the centralized bean catalog")
    p_db.add_argument("--db", help="catalog SQLite path (default: data/catalog.db)")
    db_sub = p_db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("init", help="create + seed the catalog (taxonomy + sources)")
    p_db_mig = db_sub.add_parser("migrate", help="import the manifest into the catalog")
    p_db_mig.add_argument("--manifest", help="manifest path (default: the processed manifest)")
    p_db_exp = db_sub.add_parser("export-manifest", help="export a training manifest")
    p_db_exp.add_argument("--out", help="output manifest path (default: the processed manifest)")
    p_db_exp.add_argument(
        "--all-provenance", action="store_true", help="include private (proprietary) beans too"
    )
    p_db_exp.add_argument(
        "--include-not-good", action="store_true", help="include beans flagged is_good=false"
    )
    p_db_exp.add_argument(
        "--min-trust", type=float, default=0.0, help="drop defect labels below this trust"
    )
    p_db_cur = db_sub.add_parser("curate", help="dedup + quality + lossy-label trust passes")
    p_db_cur.add_argument("--dry-run", action="store_true", help="report without writing changes")
    p_db_cur.add_argument(
        "--dedup-threshold", type=int, default=4, help="max pHash Hamming distance for a duplicate"
    )
    p_db_cur.add_argument("--min-px", type=int, default=48, help="flag crops smaller than this")
    p_db_cur.add_argument(
        "--min-stddev", type=float, default=6.0, help="flag crops below this pixel std-dev"
    )
    db_sub.add_parser("audit", help="print a catalog health report")
    p_db.set_defaults(func=cmd_db)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
