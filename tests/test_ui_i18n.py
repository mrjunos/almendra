"""Tests for the bilingual ES/EN string table."""

from __future__ import annotations

from almendra.ui.components.i18n import _STRINGS, available_languages, t


def test_default_lang_is_spanish() -> None:
    assert t("app.title") == "almendra"
    assert t("nav.home").startswith("🏠")


def test_every_key_has_both_languages() -> None:
    missing: list[str] = []
    for key, entry in _STRINGS.items():
        for lang in available_languages():
            if lang not in entry or not entry[lang]:
                missing.append(f"{key}:{lang}")
    assert not missing, f"missing translations: {missing}"


def test_unknown_key_returns_key() -> None:
    assert t("does.not.exist") == "does.not.exist"


def test_format_args() -> None:
    es = t("tray.beans_found", lang="es", n=42, total=48)
    en = t("tray.beans_found", lang="en", n=42, total=48)
    assert "42" in es and "48" in es
    assert "42" in en and "48" in en
