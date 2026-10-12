# -*- coding: utf-8 -*-
"""
Astrorust — Horoskop-Datenbank (~/.config/astrorust/profiles.json): Profile mit Gruppe, Stichwörtern
und Notizen; Import/Export als JSON oder CSV.
"""

import csv
import io
import json
import os
import uuid
import math
import copy

import aaf

CONFIG_DIR = os.path.expanduser("~/.config/astrorust")
PROFILES_PATH = os.path.join(CONFIG_DIR, "profiles.json")

# Wird beim ersten Start nicht mehr in die Datenbank eingefroren (die Zeit wäre veraltet; dafür gibt es „Jetzt“)
VOLATILE_NAME = "Aktueller Moment (Jetzt)"

DEMO_NAMES = {
    "Albert Einstein", "Johann Wolfgang von Goethe", "Carl Gustav Jung", "Marie Curie", "Leonardo da Vinci",
}

CSV_FIELDS = ["name", "year", "month", "day", "hour", "minute", "second", "timezone", "timezone_offset", "latitude",
              "longitude", "location_name", "house_system", "group", "tags", "notes"]


def _normalize(p: dict) -> dict:
    q = dict(p)
    q.setdefault("id", uuid.uuid4().hex)
    q.setdefault("group", "")
    q.setdefault("tags", [])
    q.setdefault("notes", "")
    q.setdefault("house_system", "Placidus")
    q.setdefault("timezone", None)
    q.setdefault("timezone_offset", 0.0)
    q.setdefault("second", 0)
    if isinstance(q["tags"], str):
        q["tags"] = [t.strip() for t in q["tags"].split(",") if t.strip()]
    return q


def _validate(profile):
    p = dict(profile)
    p["name"] = str(p.get("name") or "").strip()
    if not p["name"]:
        raise ValueError("Profilname fehlt.")
    for key, default in (("year", None), ("month", None), ("day", None), ("hour", 12), ("minute", 0), ("second", 0)):
        value = p.get(key, default)
        if isinstance(value, bool) or value is None or float(value) != int(value):
            raise ValueError(f"Ungültiges Profilfeld: {key}")
        p[key] = int(value)
    y, m, d = p["year"], p["month"], p["day"]
    if not 100 <= y <= 3000 or not 1 <= m <= 12:
        raise ValueError("Datum außerhalb des GUI-Bereichs (Jahr 100 bis 3000).")
    leap = y % 4 == 0 and ((y, m, d) < (1582, 10, 15) or y % 100 != 0 or y % 400 == 0)
    days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= d <= days[m - 1] or not 0 <= p["hour"] <= 23 or not 0 <= p["minute"] <= 59 or not 0 <= p["second"] <= 59:
        raise ValueError("Ungültiges Datum oder Uhrzeit im Profil.")
    for key, limit in (("latitude", 90), ("longitude", 180), ("timezone_offset", 14)):
        value = float(p.get(key, 0))
        if not math.isfinite(value) or not -limit <= value <= limit:
            raise ValueError(f"Ungültiges Profilfeld: {key}")
        p[key] = value
    for key in ("group", "notes", "location_name"):
        p[key] = str(p.get(key) or "")
    if p.get("timezone") is not None and not isinstance(p["timezone"], str):
        raise ValueError("Ungültige Zeitzone im Profil.")
    if not isinstance(p.get("tags", []), (list, str)) or any(not isinstance(t, str) for t in p.get("tags", [])):
        raise ValueError("Ungültige Stichwörter im Profil.")
    return _normalize(p)


class ProfileStore:
    def __init__(self, backend=None):
        self.backend = backend
        self.profiles: list[dict] = []
        self.load()

    # ── Laden / Speichern ──
    def load(self):
        self.profiles = []
        if os.path.exists(PROFILES_PATH):
            try:
                with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.profiles = [_normalize(p) for p in data if isinstance(p, dict) and p.get("name") != VOLATILE_NAME]
            except (OSError, ValueError) as e:
                print("Fehler beim Laden von profiles.json:", e)
        elif self.backend is not None:
            self.restore_demos(save=False)
            self.save()

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = PROFILES_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, indent=2, ensure_ascii=False)
        os.replace(tmp, PROFILES_PATH)

    # ── Änderungen ──
    def upsert(self, profile: dict) -> dict:
        """Aktualisiert ein Profil gleichen Namens oder legt es neu an."""
        p = self._put(_validate(profile))
        self.save()
        return p

    def _put(self, p):
        for i, old in enumerate(self.profiles):
            if old.get("id") == p.get("id") or old.get("name") == p.get("name"):
                p["id"] = old["id"]
                for keep in ("group", "tags", "notes"):
                    if not p.get(keep):
                        p[keep] = old.get(keep, p.get(keep))
                self.profiles[i] = p
                return p
        self.profiles.append(p)
        return p

    def delete(self, ident: str):
        self.profiles = [p for p in self.profiles if p.get("id") != ident]
        self.save()

    def clear_demos(self):
        self.profiles = [p for p in self.profiles if p.get("name") not in DEMO_NAMES]
        self.save()

    def restore_demos(self, save=True):
        if self.backend is None:
            return
        have = {p.get("name") for p in self.profiles}
        for d in self.backend.get_profiles():
            if d.get("name") == VOLATILE_NAME or d.get("name") in have:
                continue
            d = dict(d)
            d["group"] = "Demo"
            self.profiles.append(_normalize(d))
        if save:
            self.save()

    # ── Abfragen ──
    def groups(self) -> list[str]:
        return sorted({p.get("group", "") for p in self.profiles if p.get("group")})

    def search(self, text: str = "", group: str = "") -> list[dict]:
        t = text.strip().lower()
        out = []
        for p in self.profiles:
            if group and p.get("group") != group:
                continue
            hay = " ".join([p.get("name", ""), p.get("location_name", "") or "", p.get("group", ""), " ".join(p.get("tags", [])),
                            p.get("notes", ""), f"{p.get('year')}-{p.get('month'):02d}-{p.get('day'):02d}"]).lower()
            if not t or all(word in hay for word in t.split()):
                out.append(p)
        return out

    # ── Import / Export ──
    def export_json(self, path: str, profiles: list[dict] | None = None):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"format": "astrorust-profiles", "version": 1, "profiles": profiles if profiles is not None else self.profiles},
                      f, indent=2, ensure_ascii=False)

    def export_csv(self, path: str, profiles: list[dict] | None = None):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            for p in (profiles if profiles is not None else self.profiles):
                row = dict(p)
                row["tags"] = ", ".join(p.get("tags", []))
                w.writerow(row)

    def export_aaf(self, path, profiles=None):
        if self.backend is None:
            raise ValueError("AAF-Export benötigt die Rechenbibliothek.")
        text = aaf.dumps(self.profiles if profiles is None else profiles, self.backend)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def import_file(self, path: str) -> int:
        """Importiert JSON (eigenes Format oder reine Liste) oder CSV. Gibt die Zahl neuer/aktualisierter Profile zurück."""
        with open(path, "rb") as f:
            raw = f.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            if not path.lower().endswith((".aaf", ".txt")):
                raise
            text = raw.decode("cp1252")
        items: list[dict] = []
        if path.lower().endswith(".csv"):
            for row in csv.DictReader(io.StringIO(text)):
                try:
                    items.append({
                        "name": row["name"].strip(),
                        "year": int(row["year"]), "month": int(row["month"]), "day": int(row["day"]),
                        "hour": int(row.get("hour") or 12), "minute": int(row.get("minute") or 0),
                        "second": int(row.get("second") or 0),
                        "timezone": (row.get("timezone") or "").strip() or None,
                        "timezone_offset": float(row.get("timezone_offset") or 0.0),
                        "latitude": float(row["latitude"]), "longitude": float(row["longitude"]),
                        "location_name": row.get("location_name", ""),
                        "house_system": row.get("house_system") or "Placidus",
                        "group": row.get("group", ""), "tags": row.get("tags", ""), "notes": row.get("notes", ""),
                    })
                except (KeyError, ValueError) as e:
                    raise ValueError(f"Ungültige CSV-Zeile {row}: {e}")
        elif path.lower().endswith((".aaf", ".txt")):
            if self.backend is None:
                raise ValueError("AAF-Import benötigt die Rechenbibliothek.")
            items = aaf.loads(text, self.backend)
        else:
            data = json.loads(text)
            items = data["profiles"] if isinstance(data, dict) and "profiles" in data else data
            if not isinstance(items, list):
                raise ValueError("Keine Profilliste in der Datei.")
        validated = []
        for it in items:
            if not isinstance(it, dict) or not it.get("name"):
                raise ValueError("Ungültiger oder unbenannter Profildatensatz.")
            required = ("year", "month", "day", "latitude", "longitude")
            if any(k not in it for k in required):
                raise ValueError("Pflichtfelder fehlen im Profil.")
            it = dict(it)
            it.pop("id", None)  # IDs der Quelle nicht übernehmen
            validated.append(_validate(it))
        previous = copy.deepcopy(self.profiles)
        try:
            for p in validated:
                self._put(p)
            self.save()
        except Exception:
            self.profiles = previous
            raise
        return len(validated)
