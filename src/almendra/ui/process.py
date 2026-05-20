"""Subprocess wrapper for long-running tasks (training).

We don't run training inside Streamlit's process: a) it blocks the UI; b) it
ties checkpoint lifecycle to the browser tab. Instead we launch ``almendra
train`` as a subprocess and tail its live-metrics JSONL file from the UI.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TrainHandle:
    """A running training subprocess + the file it writes metrics to."""

    pid: int
    metrics_path: Path
    output_dir: Path


def start_training(
    output_dir: Path,
    overrides: list[str] | None = None,
    cwd: Path | None = None,
) -> TrainHandle:
    """Launch ``almendra train`` as a detached subprocess.

    `overrides` are Hydra-style ``key=value`` strings. The metrics file is
    placed inside ``output_dir`` so concurrent runs don't collide.
    """
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "live_metrics.jsonl"
    metrics_path.write_text("")  # clean tail target

    env = os.environ.copy()
    env["ALMENDRA_LIVE_METRICS"] = str(metrics_path)

    cmd = [sys.executable, "-m", "almendra.cli", "train", f"output_dir={output_dir}"]
    if overrides:
        cmd.extend(overrides)

    proc = subprocess.Popen(  # noqa: S603 — we build cmd ourselves
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        env=env,
        cwd=str(cwd) if cwd else None,
        start_new_session=True,
    )
    return TrainHandle(pid=proc.pid, metrics_path=metrics_path, output_dir=output_dir)


def is_running(pid: int) -> bool:
    """True if the PID is alive. Conservative: any error -> assume not running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


def stop(pid: int) -> None:
    """Best-effort SIGTERM to the training subprocess (the whole new session)."""
    if not is_running(pid):
        return
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(os.getpgid(pid), signal.SIGTERM)
