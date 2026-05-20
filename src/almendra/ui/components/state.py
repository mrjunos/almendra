"""Session-state helpers — the small amount of state the UI carries between reruns.

The UI itself is mostly stateless: each rerun reads files from disk. The pieces
that *do* survive across reruns (language toggle, running training process)
live here behind named accessors so pages don't reach into ``st.session_state``
with stringly-typed keys.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from almendra.ui.components.i18n import DEFAULT_LANG, Lang, available_languages


def current_lang() -> Lang:
    return st.session_state.get("almendra.lang", DEFAULT_LANG)


def set_lang(lang: Lang) -> None:
    st.session_state["almendra.lang"] = lang


def language_toggle() -> Lang:
    """Render a sidebar radio for ES/EN and return the active language."""
    options = available_languages()
    index = options.index(current_lang()) if current_lang() in options else 0
    pick = st.sidebar.radio(
        "🌐",
        options,
        index=index,
        format_func=lambda code: {"es": "Español", "en": "English"}.get(code, code),
        key="almendra.lang_radio",
        horizontal=True,
    )
    set_lang(pick)
    return pick


def get_state(key: str, default: Any = None) -> Any:
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    st.session_state[key] = value
