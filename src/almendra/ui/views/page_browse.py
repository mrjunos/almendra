"""Data Browser — visually inspect and spot-check the catalog.

Reads ``data/catalog.db`` directly: filter beans, see them in a thumbnail
gallery, and drill into one bean to review its views, every defect (with label
source + trust), and its lot provenance. The place to manually check the data.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from almendra.ui.components.i18n import Lang, t

_PAGE_SIZE = 24
_GALLERY_COLS = 6
_ALL = "—"


def _resolve(path: str | None) -> Path | None:
    if not path:
        return None
    from almendra.paths import processed_dir

    p = Path(path)
    return p if p.is_absolute() else processed_dir() / p


def render(lang: Lang) -> None:
    st.title(t("browse.title", lang))

    try:
        from almendra.db import queries
        from almendra.db.catalog import default_db_path, get_engine, get_session
    except ImportError as exc:
        st.error(f"catalog dependency missing: {exc} — `uv sync --extra catalog`")
        return

    db_path = default_db_path()
    if not db_path.is_file():
        st.warning(t("browse.no_db", lang))
        return

    from almendra.taxonomy import get_taxonomy

    class_names = get_taxonomy().class_names()
    engine = get_engine(db_path)

    with get_session(engine) as session:
        sources = queries.distinct_sources(session)

    # --- filters ---
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    source = c1.selectbox(t("browse.f_source", lang), [_ALL, *sources])
    split = c2.selectbox(t("browse.f_split", lang), [_ALL, "train", "val", "test"])
    defect = c3.selectbox(t("browse.f_class", lang), [_ALL, *class_names])
    provenance = c4.selectbox(
        t("browse.f_provenance", lang), [_ALL, "public_dataset", "proprietary"]
    )
    quality = c5.selectbox(t("browse.f_quality", lang), list(queries.QUALITY_OPTIONS))
    trust = c6.selectbox(t("browse.f_trust", lang), list(queries.TRUST_BUCKETS.keys()))

    filters = queries.BeanFilters(
        source=None if source == _ALL else source,
        split=None if split == _ALL else split,
        provenance=None if provenance == _ALL else provenance,
        primary_defect=None if defect == _ALL else defect,
        quality=quality,
        trust_bucket=trust,
    )

    with get_session(engine) as session:
        total, _ = queries.query_page(session, filters, limit=0, offset=0)

    if total == 0:
        st.info(t("browse.empty", lang))
        return

    pages = (total + _PAGE_SIZE - 1) // _PAGE_SIZE
    page = st.number_input(
        t("browse.page", lang, pages=pages), min_value=1, max_value=pages, value=1, step=1
    )
    offset = (int(page) - 1) * _PAGE_SIZE

    with get_session(engine) as session:
        _, rows = queries.query_page(session, filters, limit=_PAGE_SIZE, offset=offset)

    st.caption(t("browse.showing", lang, n=len(rows), total=total))

    # --- gallery ---
    cols = st.columns(_GALLERY_COLS)
    for i, row in enumerate(rows):
        col = cols[i % _GALLERY_COLS]
        flag = "" if row.is_good else " ⚠️"
        caption = f"{row.primary_defect}{flag}\n{row.ext_id}"
        image_path = _resolve(row.first_view)
        if image_path and image_path.is_file():
            col.image(str(image_path), caption=caption, use_container_width=True)
        else:
            col.caption(f"🗎 {caption}")

    # --- detail ---
    st.markdown("---")
    st.subheader(t("browse.detail", lang))
    pick = st.selectbox(t("browse.pick", lang), [r.ext_id for r in rows])
    chosen = next((r for r in rows if r.ext_id == pick), None)
    if chosen is None:
        return

    with get_session(engine) as session:
        detail = queries.bean_detail(session, chosen.id)

    left, right = st.columns([1, 1])
    with left:
        for vpath in detail.views:
            img = _resolve(vpath)
            if img and img.is_file():
                st.image(str(img), width=200)
        if not detail.is_good:
            st.warning(f"not-good — {detail.notes}")
    with right:
        st.markdown(f"**{t('browse.defects', lang)}**")
        st.dataframe(detail.defects, hide_index=True, use_container_width=True)
        st.markdown(f"**{t('browse.provenance', lang)}** · morphology: `{detail.morphology}`")
        st.json(detail.lot)
