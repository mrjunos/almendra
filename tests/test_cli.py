"""Tests for the almendra command-line interface.

The pipeline subcommands (ingest/train/eval/export/bench) are not executed here
— they need data and are exercised by the end-to-end smoke run. These tests
cover argument parsing and the `info` command.
"""

import pytest

from almendra.cli import build_parser, main


def test_info_runs_and_prints_taxonomy(capsys):
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "defect classes" in out
    assert "sound" in out


@pytest.mark.parametrize("command", ["info", "ingest", "train", "eval", "export", "bench"])
def test_parser_exposes_subcommand(command):
    args = build_parser().parse_args([command])
    assert callable(args.func)


def test_pipeline_subcommands_accept_hydra_overrides():
    args = build_parser().parse_args(["train", "model=efficientnet_b0", "seed=7"])
    assert args.overrides == ["model=efficientnet_b0", "seed=7"]


def test_eval_accepts_checkpoint_and_split():
    args = build_parser().parse_args(["eval", "--split", "val", "--checkpoint", "x.pt"])
    assert args.split == "val"
    assert args.checkpoint == "x.pt"


def test_no_command_errors():
    with pytest.raises(SystemExit):
        main([])
