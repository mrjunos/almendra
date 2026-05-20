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


PAGES = ["home", "tray", "train", "evaluate", "predict", "settings"]


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
