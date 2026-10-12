# -*- coding: utf-8 -*-
"""
Astrorust — Oberflächensprache.

Alle sichtbaren Texte im Quelltext sind deutsch und laufen durch `tr()`. Bei Sprache "en" wird
über das Wörterbuch in `i18n_en.py` übersetzt; fehlt ein Eintrag, bleibt der deutsche Text stehen.
Regelbasierte Langtexte der Rust-Bibliothek bleiben deutsch; KI-Deutungen unterstützen Deutsch und Englisch.
"""

_language = "de"
_table: dict[str, str] = {}


def set_language(lang: str) -> None:
    global _language, _table
    _language = "en" if lang == "en" else "de"
    if _language == "en":
        from i18n_en import EN
        _table = EN
    else:
        _table = {}


def language() -> str:
    return _language


def tr(text: str) -> str:
    """Übersetzt einen deutschen Text (bei 'de' unverändert)."""
    if _language == "de":
        return text
    if text in _table:
        return _table[text]
    plain = text.replace("&", "").strip()
    if plain in _table:
        return _table[plain]
    # Preserve decorative glyphs while translating the actual label.
    import re
    match = re.match(r"^([^\w—(]+)(.+)$", plain)
    if match and match[2] in _table:
        return match[1] + _table[match[2]]
    return text


def trf(template: str, **kwargs) -> str:
    """Übersetzt die Vorlage und setzt dann die Werte ein: trf("{n} Treffer", n=3)."""
    return tr(template).format(**kwargs)
