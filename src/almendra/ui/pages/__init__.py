"""Streamlit page modules — each exposes ``render(lang)``."""

from almendra.ui.pages import (
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
