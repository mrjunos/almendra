"""Tests for the almendra command-line interface."""

import pytest

from almendra.cli import main


def test_info_runs_and_prints_taxonomy(capsys):
    rc = main(["info"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "defect classes" in out
    assert "sound" in out


@pytest.mark.parametrize("command", ["train", "eval", "export", "bench"])
def test_planned_commands_run_as_stubs(command, capsys):
    rc = main([command])
    assert rc == 0
    assert "not implemented" in capsys.readouterr().out


def test_planned_command_accepts_overrides(capsys):
    # Hydra-style overrides must not break argument parsing.
    rc = main(["train", "model=efficientnet_b0", "train.epochs=5"])
    assert rc == 0


def test_no_command_errors():
    with pytest.raises(SystemExit):
        main([])
