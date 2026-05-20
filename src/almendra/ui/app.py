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
from almendra.ui.pages import (
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


def render_sidebar() -> str:
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
    pick = st.sidebar.radio(
        label="nav",
        options=list(pages.keys()),
        format_func=lambda key: pages[key],
        label_visibility="collapsed",
        key="almendra.page",
    )
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
