"""Streamlit entry point for the local almendra UI.

Run via ``almendra ui`` (which exec's ``streamlit run`` on this file). The app
uses Streamlit's classic radio-based navigation rather than the
``st.Page``/``st.navigation`` multipage API so the tests can drive each page
directly without spinning up a server.
"""

from __future__ import annotations

import streamlit as st

from almendra.ui.components.i18n import t
from almendra.ui.components.state import current_lang, language_toggle
from almendra.ui.views import (
    page_evaluate,
    page_home,
    page_predict,
    page_settings,
    page_train,
    page_tray,
)


def configure_page() -> None:
    st.set_page_config(
        page_title="almendra",
        page_icon="☕",
        layout="wide",
        initial_sidebar_state="expanded",
    )


_PAGE_KEY = "almendra.current_page"
_PENDING_KEY = "almendra.pending_page"
_RADIO_KEY = "almendra.page_radio"


def render_sidebar() -> str:
    """Render the sidebar and return the active page key.

    Navigation has two entry points: the sidebar radio (user clicks an option)
    and the wizard buttons on Home (programmatic switch). Streamlit normally
    refuses to let outside code reassign a widget's session_state key after it
    has been instantiated, so to honour the wizard's request we *delete* the
    radio's own key — that forces Streamlit to re-init the widget with our
    ``index=`` on the next render. Source of truth lives in ``_PAGE_KEY`` (a
    plain non-widget key).
    """
    lang = language_toggle()
    st.sidebar.markdown(f"### {t('app.title', lang)}")
    st.sidebar.caption(t("app.tagline", lang))
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**{t('sidebar.nav', lang)}**")
    pages = {
        "home": t("nav.home", lang),
        "tray": t("nav.tray", lang),
        "train": t("nav.train", lang),
        "evaluate": t("nav.evaluate", lang),
        "predict": t("nav.predict", lang),
        "settings": t("nav.settings", lang),
    }
    keys = list(pages.keys())

    pending = st.session_state.pop(_PENDING_KEY, None)
    if pending in keys:
        # Drop the radio's remembered pick so ``index=`` actually takes effect.
        st.session_state.pop(_RADIO_KEY, None)
        st.session_state[_PAGE_KEY] = pending

    current = st.session_state.get(_PAGE_KEY, "home")
    index = keys.index(current) if current in keys else 0

    pick = st.sidebar.radio(
        label="nav",
        options=keys,
        index=index,
        format_func=lambda key: pages[key],
        label_visibility="collapsed",
        key=_RADIO_KEY,
    )
    # Mirror the radio's pick into our source-of-truth key so the next rerun
    # starts on the same page.
    st.session_state[_PAGE_KEY] = pick
    return pick


def main() -> None:
    configure_page()
    page = render_sidebar()
    lang = current_lang()
    if page == "home":
        page_home.render(lang)
    elif page == "tray":
        page_tray.render(lang)
    elif page == "train":
        page_train.render(lang)
    elif page == "evaluate":
        page_evaluate.render(lang)
    elif page == "predict":
        page_predict.render(lang)
    elif page == "settings":
        page_settings.render(lang)


main()
