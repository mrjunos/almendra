"""Streamlit smoke tests — each page renders without raising.

Uses ``streamlit.testing.v1.AppTest`` to drive each page in-process. We invoke
each page's ``render(lang)`` from a tiny driver script so the test does not
depend on the sidebar navigation state.
"""

from __future__ import annotations

import inspect
import textwrap
from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = streamlit_testing.AppTest


PAGES = ["home", "tray", "train", "evaluate", "quantize", "predict", "settings"]


def _driver_script(page: str, lang: str) -> str:
    """A standalone Streamlit script that imports and runs one page."""
    return textwrap.dedent(
        f"""
        from almendra.ui.views import page_{page}
        page_{page}.render({lang!r})
        """
    ).strip()


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("lang", ["es", "en"])
def test_page_renders_without_exception(tmp_path: Path, page: str, lang: str) -> None:
    script_path = tmp_path / f"driver_{page}_{lang}.py"
    script_path.write_text(_driver_script(page, lang))
    at = AppTest.from_file(str(script_path), default_timeout=30)
    at.run()
    assert not at.exception, f"{page}/{lang} raised: {[e.value for e in at.exception]}"


def test_render_signature_consistent() -> None:
    """Every page module must expose ``render(lang)`` — keeps the dispatcher honest."""
    from almendra.ui import views

    for page in PAGES:
        module = getattr(views, f"page_{page}")
        sig = inspect.signature(module.render)
        assert "lang" in sig.parameters, f"page_{page}.render must accept lang"


_APP_PATH = Path(__file__).resolve().parents[1] / "src" / "almendra" / "ui" / "app.py"


@pytest.mark.parametrize(
    "key,expected_page",
    [
        ("wizard_tray", "tray"),
        ("wizard_train", "train"),
        ("wizard_eval", "evaluate"),
    ],
)
def test_home_wizard_navigates_via_full_app(key: str, expected_page: str) -> None:
    """Driving the *full* app (not just one page), clicking each wizard button
    must navigate to the matching page without raising.

    Regression test for: writing to the sidebar radio's own session_state key
    raised ``StreamlitAPIException`` on the first manual E2E run. The fix uses
    an ``on_click`` callback that sets a non-widget ``almendra.pending_page``;
    the sidebar then resolves it before rendering the radio on the next rerun.
    """
    at = AppTest.from_file(str(_APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception, f"initial render raised: {[e.value for e in at.exception]}"
    assert at.title[0].value == "Inicio"
    wizard = [b for b in at.button if b.key == key]
    assert wizard, f"button {key!r} missing from Home wizard"
    wizard[0].click().run()
    assert not at.exception, f"clicking {key} raised: {[e.value for e in at.exception]}"
    assert at.session_state["almendra.current_page"] == expected_page
