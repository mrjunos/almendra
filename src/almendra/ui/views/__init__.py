"""Streamlit page modules — each exposes ``render(lang)``.

The directory is named ``views/`` (not ``pages/``) so Streamlit does not
auto-discover it as its multi-page navigation. The app uses its own sidebar
radio for navigation.
"""

from almendra.ui.views import (
    page_evaluate,
    page_home,
    page_predict,
    page_settings,
    page_train,
    page_tray,
)

__all__ = [
    "page_home",
    "page_tray",
    "page_train",
    "page_evaluate",
    "page_predict",
    "page_settings",
]
