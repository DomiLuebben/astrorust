# -*- coding: utf-8 -*-
"""
Astrorust — Programmeinstellungen (~/.config/astrorust/settings.json)

Enthält die Berechnungsoptionen (werden als `settings` an die Rust-Bibliothek gereicht)
und Oberflächenoptionen (Sprache, Häusersystem, Lesezeichen).
"""

import copy
import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/astrorust")
SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")

# Standard = bisheriges Verhalten der Software
DEFAULTS = {
    "language": "de",            # "de" | "en"
    "house_system": "Placidus",
    "calc": {
        "node": "True",           # "True" | "Mean"
        "lilith": "Mean",         # "Mean" | "Osculating"
        "asteroids": False,       # Ceres, Pallas, Juno, Vesta
        "south_node": False,
        "zodiac": "Tropical",     # "Tropical" | "Sidereal"
        "ayanamsa": 1,            # Lahiri
        "topocentric": False,
        "orbs": {},               # {"Conjunction": 8.0, ...}
        "luminary_bonus": 1.5,
        "minor_point_reduction": 1.5,
        "aspects": ["Conjunction", "Opposition", "Trine", "Square", "Sextile", "Quincunx",
                    "SemiSquare", "Sesquiquadrate", "SemiSextile", "Quintile"],
        "fixed_stars": True,
        "fixed_star_orb": 1.0,
        "analysis": True,
    },
}

ASPECT_KEYS = [
    ("Conjunction", "Konjunktion", "☌", 8.0),
    ("Opposition", "Opposition", "☍", 8.0),
    ("Trine", "Trigon", "△", 7.0),
    ("Square", "Quadrat", "□", 7.0),
    ("Sextile", "Sextil", "⚹", 5.0),
    ("Quincunx", "Quinkunx", "⚻", 3.0),
    ("SemiSquare", "Halbquadrat", "∠", 2.5),
    ("Sesquiquadrate", "Anderthalbquadrat", "⚼", 2.5),
    ("SemiSextile", "Halbsextil", "⚺", 2.0),
    ("Quintile", "Quintil", "Q", 2.0),
]


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict) and key != "orbs":
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


class AppSettings:
    """Dünner Wrapper um das Einstellungs-Dict; jede Instanz ist eine unabhängige Kopie."""

    def __init__(self, data: dict | None = None):
        self.data = _merge(DEFAULTS, data or {})

    @classmethod
    def load(cls) -> "AppSettings":
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                return cls(json.load(f))
        except (OSError, ValueError):
            return cls()

    def save(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = SETTINGS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, SETTINGS_PATH)

    # Bequemer Zugriff
    @property
    def language(self) -> str:
        return self.data.get("language", "de")

    @property
    def house_system(self) -> str:
        return self.data.get("house_system", "Placidus")

    def calc_settings(self, **overrides) -> dict:
        """Das `settings`-Objekt für die Rust-Anfragen."""
        s = copy.deepcopy(self.data["calc"])
        s["language"] = self.language
        s.update(overrides)
        return s

    @property
    def sidereal(self) -> bool:
        return self.data["calc"].get("zodiac") == "Sidereal"
