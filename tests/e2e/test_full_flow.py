"""Happy-path E2E visual test — drives the real UI through the whole pipeline.

Launches ``almendra ui`` against an isolated sandbox seeded with a tiny real
dataset, then drives a browser through Tray → Train → Evaluate → Quantize →
Predict and records the whole run to a ``.webm``. One test, also the CI gate.

Run it::

    uv run pytest -m e2e                 # headless, records video
    PWHEADED=1 uv run pytest -m e2e      # watch it live

Sibling modules (``harness``, ``synth_tray``) are imported directly — pytest's
prepend import mode puts ``tests/e2e/`` on ``sys.path``.
"""

from __future__ import annotations

import contextlib
import os
import signal
import time
from pathlib import Path

import harness
import pytest
from synth_tray import make_tray

from almendra.datasets.tray import TraySpec

pytestmark = pytest.mark.e2e

# Hard dependencies for this test (skip cleanly if absent rather than erroring).
pytest.importorskip("playwright.sync_api")
cv2 = pytest.importorskip("cv2")

_RECORDINGS = Path(__file__).resolve().parent / "recordings"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "processed"

# 6×8 matches the Tray page's default rows/cols, so the test changes no widgets there.
_TRAY_SPEC = TraySpec(rows=6, cols=8)
_OCCUPIED = [(0, 0), (0, 7), (1, 3), (2, 5), (3, 1), (4, 6), (5, 0), (5, 7)]


def _bean_crops() -> list[Path]:
    files = sorted(_FIXTURE.glob("roboflow_robusta_defects/*/*.png"))
    assert files, "fixture missing — run `uv run python -m tests.e2e.build_fixture`"
    return files


def _wait_idle(page) -> None:
    """Let a Streamlit rerun start and settle (the top-right status widget)."""
    status = page.locator('[data-testid="stStatusWidget"]')
    with contextlib.suppress(Exception):
        status.wait_for(state="visible", timeout=2_000)
    with contextlib.suppress(Exception):
        status.wait_for(state="hidden", timeout=120_000)


def _nav(page, label: str) -> None:
    """Click a sidebar nav option by its (English) label."""
    page.locator('[data-testid="stSidebar"]').get_by_text(label, exact=False).first.click()
    _wait_idle(page)


def _terminate(proc) -> None:
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        proc.terminate()


def test_full_flow(tmp_path: Path) -> None:
    from playwright.sync_api import expect, sync_playwright

    sandbox = harness.build_sandbox(tmp_path)

    # Synthetic side-A tray photo built from real crops.
    crops = _bean_crops()
    tray_imgs = {w: cv2.imread(str(crops[i % len(crops)])) for i, w in enumerate(_OCCUPIED)}
    tray_png = tmp_path / "tray_side_a.png"
    cv2.imwrite(str(tray_png), make_tray(_TRAY_SPEC, tray_imgs))
    bean_png = crops[0]  # one crop for Predict

    rec_dir = _RECORDINGS / time.strftime("%Y%m%d-%H%M%S")
    rec_dir.mkdir(parents=True, exist_ok=True)

    port = harness.free_port()
    server = harness.start_ui(sandbox, port)
    video_path: str | None = None
    try:
        harness.wait_until_ready(port, timeout=90)
        headed = os.environ.get("PWHEADED") == "1"
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not headed)
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(rec_dir),
                record_video_size={"width": 1440, "height": 900},
            )
            page = context.new_page()
            page.set_default_timeout(30_000)
            page.goto(f"http://127.0.0.1:{port}/")

            # Switch UI to English for stable, readable selectors.
            expect(page.get_by_text("English", exact=True)).to_be_visible(timeout=30_000)
            page.get_by_text("English", exact=True).click()
            _wait_idle(page)

            # 1) TRAY — upload synthetic tray, segment, save crops.
            _nav(page, "Tray Capture")
            page.locator('input[type="file"]').first.set_input_files(str(tray_png))
            _wait_idle(page)
            page.get_by_role("button", name="Process photos").click()
            expect(page.get_by_text("beans found")).to_be_visible(timeout=60_000)
            page.get_by_role("button", name="Save crops").click()
            expect(page.get_by_text("Saved to")).to_be_visible(timeout=30_000)

            # 2) TRAIN — 1 epoch on the tiny dataset; wait for completion.
            _nav(page, "Train")
            epochs = page.locator('[data-testid="stNumberInput"] input').first
            epochs.fill("1")
            epochs.press("Enter")
            _wait_idle(page)
            page.get_by_role("button", name="Start training").click()
            expect(page.get_by_text("Done")).to_be_visible(timeout=300_000)

            # 3) EVALUATE — latest checkpoint auto-selected, split=test.
            _nav(page, "Evaluate")
            page.get_by_role("button", name="Run", exact=True).click()
            expect(page.get_by_text("Accuracy")).to_be_visible(timeout=120_000)

            # 4) QUANTIZE — export float ONNX + dynamic INT8.
            _nav(page, "Quantize")
            page.get_by_role("button", name="Export / Quantize").click()
            expect(page.get_by_text("Exported")).to_be_visible(timeout=120_000)
            run_dir = sandbox / "outputs"
            onnx = list(run_dir.glob("*/model.onnx"))
            int8 = list(run_dir.glob("*/model.int8.onnx"))
            assert onnx, "float ONNX not written"
            assert int8, "INT8 ONNX not written"

            # 5) PREDICT — compare float vs INT8 on one bean.
            _nav(page, "Predict")
            page.get_by_text("Compare float vs INT8").click()
            _wait_idle(page)
            page.locator('input[type="file"]').first.set_input_files(str(bean_png))
            expect(page.get_by_text("Agreement")).to_be_visible(timeout=60_000)

            video_path = page.video.path() if page.video else None
            context.close()  # flush the video to disk
            browser.close()
    finally:
        _terminate(server)

    if video_path:
        print(f"\nE2E recording: {video_path}")
        assert Path(video_path).is_file()
