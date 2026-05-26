"""Settings page — taxonomy, data sources, current config, paths."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from almendra.ui.components.i18n import Lang, t
from almendra.ui.discovery import manifest_path, outputs_root, project_root


def _read_yaml(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"# could not read {path}: {exc}"


def _source_summary(sources_dir: Path) -> list[dict]:
    """One row per adapter: name, species, licence, commercial use, status."""
    rows: list[dict] = []
    for path in sorted(sources_dir.glob("*.yaml")):
        try:
            cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        rows.append(
            {
                "source": cfg.get("name", path.stem),
                "species": cfg.get("species", "—"),
                "license": cfg.get("license", "—"),
                "commercial": cfg.get("commercial_use"),
                "status": cfg.get("status", "—"),
            }
        )
    return rows


def render(lang: Lang) -> None:
    st.title(t("settings.title", lang))

    st.subheader(t("settings.taxonomy", lang))
    try:
        from almendra.taxonomy import get_taxonomy

        tax = get_taxonomy()
        rows = [
            {
                "index": c.index,
                "class": c.name,
                "category": c.category_name,
                "accept": c.accept,
                "full_defect_equivalent": c.full_defect_equivalent,
            }
            for c in sorted(tax.defect_classes.values(), key=lambda c: c.index)
        ]
        st.dataframe(rows, hide_index=True, use_container_width=True)
        st.caption(
            f"schema v{tax.schema_version} · {'verified' if tax.verified else 'provisional'}"
        )
    except Exception as exc:
        st.error(f"taxonomy unavailable: {exc}")

    st.subheader(t("settings.sources", lang))
    sources_dir = project_root() / "data" / "sources"
    if sources_dir.is_dir():
        summary = _source_summary(sources_dir)
        if summary:
            st.dataframe(summary, hide_index=True, use_container_width=True)
            blocked = [r["source"] for r in summary if r["status"] == "license_unverified"]
            if blocked:
                st.warning(t("settings.sources_blocked", lang, sources=", ".join(blocked)))
        for yaml_path in sorted(sources_dir.glob("*.yaml")):
            with st.expander(yaml_path.stem):
                st.code(_read_yaml(yaml_path), language="yaml")
    else:
        st.caption("no `data/sources/` directory")

    st.subheader(t("settings.config", lang))
    cfg_path = project_root() / "configs" / "config.yaml"
    if cfg_path.is_file():
        st.code(_read_yaml(cfg_path), language="yaml")

    st.subheader(t("settings.paths", lang))
    st.markdown(
        f"- **project**: `{project_root()}`\n"
        f"- **outputs**: `{outputs_root()}`\n"
        f"- **manifest**: `{manifest_path()}` "
        f"({'✅' if manifest_path().is_file() else '❌'})"
    )
