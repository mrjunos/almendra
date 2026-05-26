"""E2E sandbox + server harness.

The UI form can only set a few training knobs; infra knobs (pretrained off,
num_workers, device, quantize mode) have to come from the config. So we build a
throwaway *sandbox* repo per run: a copy of ``configs/`` tweaked for fast/offline
runs, plus the committed mini-dataset as ``data/processed/``. Pointing
``ALMENDRA_ROOT`` at the sandbox redirects config+data; launching the UI with
``cwd=sandbox`` redirects ``outputs/`` (discovery walks up from CWD).
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PROCESSED = Path(__file__).resolve().parent / "fixtures" / "processed"

# Targeted text edits on the copied configs. Each (file, old, new) must apply
# exactly once, or build_sandbox raises — so an upstream config change fails
# loudly instead of silently running slow/online.
_CONFIG_TWEAKS = [
    ("model/mobilenetv3_small.yaml", "pretrained: true", "pretrained: false"),
    ("data/public_baseline.yaml", "num_workers: 4", "num_workers: 0"),
    ("data/public_baseline.yaml", "image_size: 224", "image_size: 160"),
    ("config.yaml", "device: auto", "device: cpu"),
    ("export/onnx_int8.yaml", "mode: int8_static", "mode: int8_dynamic"),
    ("export/onnx_int8.yaml", "num_samples: 64", "num_samples: 8"),
]


def build_sandbox(root: Path) -> Path:
    """Materialise a self-contained sandbox repo under ``root``; return its path."""
    sandbox = root / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)

    # A pyproject.toml so discovery.project_root() (walks up from CWD) stops here.
    (sandbox / "pyproject.toml").write_text("[project]\nname = 'almendra-e2e-sandbox'\n")

    shutil.copytree(REPO_ROOT / "configs", sandbox / "configs")
    for rel, old, new in _CONFIG_TWEAKS:
        path = sandbox / "configs" / rel
        text = path.read_text()
        if text.count(old) != 1:
            raise RuntimeError(f"config tweak failed: {old!r} not found exactly once in {rel}")
        path.write_text(text.replace(old, new))

    if not (FIXTURE_PROCESSED / "manifest.jsonl").is_file():
        raise RuntimeError(
            "mini-dataset fixture missing — run `uv run python -m tests.e2e.build_fixture`"
        )
    shutil.copytree(FIXTURE_PROCESSED, sandbox / "data" / "processed")
    return sandbox


def sandbox_env(sandbox: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["ALMENDRA_ROOT"] = str(sandbox)
    env["ALMENDRA_TAXONOMY"] = str(REPO_ROOT / "data" / "taxonomy.yaml")
    return env


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_ui(sandbox: Path, port: int) -> subprocess.Popen:
    """Launch ``almendra ui --headless`` against the sandbox."""
    cmd = [sys.executable, "-m", "almendra.cli", "ui", "--headless", "--port", str(port)]
    return subprocess.Popen(
        cmd,
        cwd=str(sandbox),
        env=sandbox_env(sandbox),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def build_catalog(sandbox: Path) -> None:
    """Build the sandbox catalog from the fixture manifest (also exercises `db migrate`)."""
    cmd = [sys.executable, "-m", "almendra.cli", "db", "migrate"]
    subprocess.run(  # noqa: S603 — we build cmd ourselves
        cmd,
        cwd=str(sandbox),
        env=sandbox_env(sandbox),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )


def wait_until_ready(port: int, timeout: float = 60.0) -> None:
    url = f"http://127.0.0.1:{port}/_stcore/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Streamlit did not become ready on port {port} within {timeout}s")
