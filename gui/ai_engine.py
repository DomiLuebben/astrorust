# -*- coding: utf-8 -*-
"""
Astrorust — KI-Deutungsengine (Multi-Provider: Claude CLI, Codex CLI, Ollama, API-Keys, GenOffice-Import)
"""

import copy
import json
import os
import shutil
import signal
import subprocess
import selectors
import codecs
import time
import tempfile
import urllib.parse
import urllib.request
import urllib.error
import ssl
from PyQt6.QtCore import QThread, pyqtSignal

# Workers waiting for a network timeout must outlive closed chart widgets.
_PENDING_WORKERS = set()


def retain_worker(worker):
    _PENDING_WORKERS.add(worker)
    worker.finished.connect(lambda: _PENDING_WORKERS.discard(worker))
    if not worker.isRunning():
        _PENDING_WORKERS.discard(worker)

ASTRORUST_CONFIG_DIR = os.path.expanduser("~/.config/astrorust")
ASTRORUST_AI_SETTINGS = os.path.join(ASTRORUST_CONFIG_DIR, "ai_settings.json")


class AiConfig:
    DEFAULT_CONFIG = {
        "active_provider": "auto",  # 'claude_cli', 'codex_cli', 'ollama', 'anthropic', 'openai', 'gemini', 'openrouter', 'custom'
        "ollama_url": "http://127.0.0.1:11434",
        "ollama_model": "mistral",
        "custom_url": "http://127.0.0.1:1234/v1",
        "custom_model": "local-model",
        "api_keys": {
            "anthropic": "",
            "openai": "",
            "gemini": "",
            "deepseek": "",
            "openrouter": "",
            "mistral": "",
            "custom": "",
        },
        "models": {
            "anthropic": "claude-sonnet-5-5",
            "openai": "gpt-4o",
            "gemini": "gemini-2.5-pro",
            "openrouter": "deepseek/deepseek-chat",
            "deepseek": "deepseek-chat",
        }
    }

    @classmethod
    def load(cls):
        os.makedirs(ASTRORUST_CONFIG_DIR, exist_ok=True)
        if os.path.exists(ASTRORUST_AI_SETTINGS):
            try:
                with open(ASTRORUST_AI_SETTINGS, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                # Tiefes Mergen: neue Standard-Schlüssel (z. B. ein später ergänzter Provider)
                # tauchen auch in alten Konfigurationsdateien auf; DEFAULT_CONFIG bleibt unverändert.
                merged = copy.deepcopy(cls.DEFAULT_CONFIG)
                for key, value in cfg.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        merged[key].update(value)
                    else:
                        merged[key] = value
                return merged
            except Exception as e:
                print("Fehler beim Laden der KI-Einstellungen:", e)

        # Erster Start: mit Standardwerten initialisieren
        cfg = copy.deepcopy(cls.DEFAULT_CONFIG)
        cls.save(cfg)
        return cfg

    @classmethod
    def save(cls, config_dict):
        os.makedirs(ASTRORUST_CONFIG_DIR, exist_ok=True)
        try:
            # API-Schlüssel stehen im Klartext in der Datei: nur für den Benutzer lesbar anlegen
            # (ohne dieses Flag erzeugt open() sie mit 0644, also weltlesbar).
            fd = os.open(ASTRORUST_AI_SETTINGS, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            os.chmod(ASTRORUST_AI_SETTINGS, 0o600)
        except Exception as e:
            print("Fehler beim Speichern der KI-Einstellungen:", e)


def detect_environment():
    """Erkennt automatisch installierte CLI-Agenten und lokale Endpunkte"""
    results = {
        "claude_cli": shutil.which("claude") or (os.path.exists(os.path.expanduser("~/.local/bin/claude")) and os.path.expanduser("~/.local/bin/claude")),
        "codex_cli": shutil.which("codex") or (os.path.exists(os.path.expanduser("~/.local/bin/codex")) and os.path.expanduser("~/.local/bin/codex")),
        "ollama_running": False,
        "ollama_models": [],
    }

    # Check Ollama
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "Astrorust"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results["ollama_running"] = True
            results["ollama_models"] = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    return results


# ========================================================
# Astrologischer Prompt-Generator (Feature-Parität mit Astroplus)
# ========================================================

def _planet_lines(c):
    lines = []
    for p in c.get("planets", []):
        dig = f", Würde: {p['dignity']}" if p.get("dignity") else ""
        rx = " [RÜCKLÄUFIG ℞]" if p.get("is_retrograde") else ""
        lines.append(f"- {p['name']} ({p['glyph']}): {p['formatted_deg']} in {p['sign_name']} (Haus {p['house']}){dig}{rx}")
    return lines


def format_analysis(c):
    """Strukturierte Zusatzanalysen (klassische Würden, Figuren, Halbsummen …) für den Prompt."""
    a = c.get("analysis")
    if not a:
        return ""
    out = []
    out.append("SEKTE: " + ("Tageshoroskop" if a.get("is_diurnal") else "Nachthoroskop"))
    if a.get("dignities"):
        out.append("KLASSISCHE WÜRDEN (Lilly-Wertung, positiv = gestärkt):")
        for d in a["dignities"]:
            out.append(f"- {d['planet_name']} in {d['sign_name']}: {d['score']:+d} ({d['summary']})")
    if a.get("receptions"):
        out.append("REZEPTIONEN: " + "; ".join(f"{r['planet_a']}–{r['planet_b']}: {r['kind']}" for r in a["receptions"]))
    if a.get("final_dispositor"):
        out.append(f"ENDDISPOSITOR: {a['final_dispositor']}")
    if a.get("patterns"):
        out.append("ASPEKTFIGUREN: " + "; ".join(f"{p['name']} ({', '.join(p['points'])})" for p in a["patterns"]))
    if a.get("chart_shape"):
        out.append(f"HOROSKOPFORM: {a['chart_shape']['name']}")
    d = a.get("distribution")
    if d:
        out.append(f"VERTEILUNG: über dem Horizont {d['above_horizon']}, darunter {d['below_horizon']}; Quadranten I–IV: {d['quadrants']}; "
                   f"betonte Häusergruppe: {d['dominant_house_group']}")
    if a.get("lots"):
        out.append("ARABISCHE LOSE: " + "; ".join(f"{l['name']} {l['formatted']} {l['sign_name']} (Haus {l['house']})" for l in a["lots"][:6]))
    if a.get("fixed_stars"):
        out.append("FIXSTERNE (Konjunktionen): " + "; ".join(f"{s['star']} ☌ {s['contact']} ({s['formatted_orb']})" for s in a["fixed_stars"][:10]))
    if a.get("midpoint_hits"):
        out.append("HALBSUMMENBILDER (90°-Scheibe, engste): " + "; ".join(
            f"{h['point']} = {h['a']}/{h['b']} ({h['formatted_orb']})" for h in a["midpoint_hits"][:10]))
    if a.get("parallels"):
        out.append("PARALLELEN: " + "; ".join(f"{p['planet_a']} {p['kind']} {p['planet_b']}" for p in a["parallels"][:8]))
    return "\n".join(out)


def format_astrology_data(chart, extras=None):
    c = chart
    extras = extras or {}
    p_lines = _planet_lines(c)

    h_lines = []
    for h in c.get("houses", []):
        cusp_name = {1: " (Aszendent / AC)", 10: " (Medium Coeli / MC)", 7: " (Deszendent / DC)", 4: " (Imum Coeli / IC)"}.get(h["house_number"], "")
        h_lines.append(f"- Haus {h['house_number']}{cusp_name}: {h['formatted_deg']} in {h['sign_name']}")

    asp_lines = []
    for asp in c.get("aspects", [])[:22]:
        app_str = "applikativ" if asp.get("is_applying") else "separativ"
        asp_lines.append(f"- {asp['point_a_name']} {asp['aspect_name']} {asp['point_b_name']} (Orb: {asp['formatted_orb']}, {app_str}, Winkel: {asp['actual_angle']:.2f}°)")

    eq = c.get("element_quality", {})
    eq_summary = (
        f"Elemente: Feuer={eq.get('fire')}, Erde={eq.get('earth')}, Luft={eq.get('air')}, Wasser={eq.get('water')} "
        f"(Dominant: {eq.get('dominant_element')})\n"
        f"Qualitäten: Kardinal={eq.get('cardinal')}, Fix={eq.get('fixed')}, Veränderlich={eq.get('mutable')} "
        f"(Dominant: {eq.get('dominant_quality')})"
    )
    zodiac = ""
    if c.get("zodiac") == "Sidereal":
        zodiac = f"\nTierkreis: SIDERISCH (Ayanamsa {c.get('ayanamsa_name')}, {c.get('ayanamsa_value', 0):.4f}°) – alle Positionen sind siderisch."
    tzinfo = c.get("timezone_info") or {}
    tznote = f"\nZeitzone: {tzinfo['note']}" if tzinfo.get("note") else ""

    text = f"""GEBURTSDATEN:
Name: {c.get('name')}
Zeitpunkt: {c.get('date_time')}{tznote}
Ort: {c.get('location_name')} ({c.get('latitude'):.4f}° N/S, {c.get('longitude'):.4f}° E/W)
Häusersystem: {c.get('house_system')}{zodiac}
Aszendent (AC): {c.get('angles', {}).get('ascendant_formatted')}
Medium Coeli (MC): {c.get('angles', {}).get('midheaven_formatted')}

PLANETENPOSITIONEN:
{chr(10).join(p_lines)}

HÄUSERSPITZEN:
{chr(10).join(h_lines)}

BEDEUTENDE ASPEKTE (sortiert nach engstem Orbis):
{chr(10).join(asp_lines)}

ELEMENTE & QUALITÄTEN:
{eq_summary}
"""
    analysis = format_analysis(c)
    if analysis:
        text += f"\nZUSATZANALYSEN:\n{analysis}\n"

    if extras.get("transit"):
        tc = extras["transit"]
        tr_lines = [f"- Transit-{p['name']}: {p['formatted_deg']} in {p['sign_name']}{' [℞]' if p.get('is_retrograde') else ''}" for p in tc.get("planets", [])]
        text += f"\nAKTUELLE TRANSITE:\nZeitpunkt der Transite: {tc.get('date_time')}\n" + "\n".join(tr_lines)
        if extras.get("transit_aspects"):
            text += "\nTransit-Aspekte zum Radix (engste):\n" + "\n".join(
                f"- Transit-{a['transit_name']} {a['aspect_name']} Radix-{a['natal_name']} (Orb {a['formatted_orb']})" for a in extras["transit_aspects"][:20])

    if extras.get("partner"):
        pc = extras["partner"]
        syn_lines = [f"- {pc.get('name')} {p['name']}: {p['formatted_deg']} in {p['sign_name']} (Haus {p['house']})" for p in pc.get("planets", [])]
        text += f"\n\nPARTNER-HOROSKOP ({pc.get('name')}):\nZeitpunkt: {pc.get('date_time')}\n" + "\n".join(syn_lines)
        if extras.get("cross_aspects"):
            text += "\nAspekte zwischen den Horoskopen (engste):\n" + "\n".join(
                f"- {a['transit_name']} (A) {a['aspect_name']} {a['natal_name']} (B) (Orb {a['formatted_orb']})" for a in extras["cross_aspects"][:24])
        if extras.get("composite"):
            cc = extras["composite"]
            text += f"\nCOMPOSITE-HOROSKOP: AC {cc['angles']['ascendant_formatted']}, MC {cc['angles']['midheaven_formatted']}\n" + "\n".join(_planet_lines(cc))
        if extras.get("davison"):
            dc = extras["davison"]
            text += f"\nDAVISON-HOROSKOP ({dc.get('date_time')}): AC {dc['angles']['ascendant_formatted']}, MC {dc['angles']['midheaven_formatted']}\n" + "\n".join(_planet_lines(dc))

    if extras.get("progression"):
        pr = extras["progression"]
        pc = pr["progressed_chart"]
        text += f"\n\nPROGRESSION ({pr['kind_label']}, Alter {pr['age_years']:.1f}, Solarbogen {pr['solar_arc']:.2f}°):\n" + "\n".join(_planet_lines(pc))
        text += f"\nProgr. AC {pc['angles']['ascendant_formatted']}, MC {pc['angles']['midheaven_formatted']}"
        if pr.get("moon_phase"):
            text += f"\nProgressive Mondphase: {pr['moon_phase']}"
        text += "\nProgressions-Aspekte zum Radix:\n" + "\n".join(
            f"- Progr. {a['transit_name']} {a['aspect_name']} Radix-{a['natal_name']} (Orb {a['formatted_orb']})" for a in pr["aspects_to_natal"][:24])

    if extras.get("return"):
        rt = extras["return"]
        rc = rt["chart"]
        text += f"\n\nRETURN-HOROSKOP ({rc['name']}, {rc['date_time']}, {rc['location_name']}): AC {rc['angles']['ascendant_formatted']}, MC {rc['angles']['midheaven_formatted']}\n" + "\n".join(_planet_lines(rc))
        text += "\nReturn-Aspekte zum Radix:\n" + "\n".join(
            f"- Return-{a['transit_name']} {a['aspect_name']} Radix-{a['natal_name']} (Orb {a['formatted_orb']})" for a in rt["aspects_to_natal"][:20])

    if extras.get("vedic"):
        v = extras["vedic"]
        text += f"\n\nVEDISCHE DATEN (siderisch, {v['ayanamsa_name']}): Lagna {v['lagna']}, Mond-Nakshatra {v['moon_nakshatra']}\n"
        text += "\n".join(f"- {p['name']} ({p['sanskrit']}): {p['rashi']}, Haus {p['house']}, {p['nakshatra']} Pada {p['pada']}, Herr {p['nakshatra_lord']}, {p['dignity']}" for p in v["planets"])
        cur = [d for d in v["dasha"] if d["current"]]
        if cur:
            subs = [s for s in cur[0]["sub_periods"] if s["current"]]
            text += f"\nLaufende Mahadasha: {cur[0]['lord']} ({cur[0]['start']} – {cur[0]['end']})"
            if subs:
                text += f", Antardasha {subs[0]['lord']} ({subs[0]['start']} – {subs[0]['end']})"
        d9 = next((x for x in v["vargas"] if x["key"] == "D9"), None)
        if d9:
            text += "\nNavamsa (D9): " + ", ".join(f"{p['point']} {p['rashi']}" for p in d9["placements"])

    if extras.get("astromap"):
        am = extras["astromap"]
        text += "\n\nASTROKARTOGRAFIE (Orte nahe an Planetenlinien, Abstand in Längengraden):\n" + "\n".join(
            f"- {c['city']} ({c['country']}): " + ", ".join(f"{h['glyph']}{h['body']} {h['kind']} {h['distance_deg']:.1f}°" for h in c["hits"][:4])
            for c in am["cities"][:25])

    return text


MODULE_PROMPTS = {
    "gesamt": """Erstelle eine fundierte, psychologisch tiefgründige Radix-Gesamtanalyse für dieses Geburtshoroskop (im Stil der psychologischen Astrologie von Liz Greene, C.G. Jung und Anita Cortesi / Astroplus).
Strukturiere die Analyse in folgende Kapitel:
1. Der Wesenskern: Synthese aus Sonne, Mond und Aszendent (Das persönliche Dreieck).
2. Seelische Dynamik & emotionale Veranlagung (Mond, 4. Haus, Wasser/Erde-Gewichtung).
3. Geist, Kommunikation & Handlungskraft (Merkur, Mars, Feuer/Luft).
4. Herausforderungen, Schattenarbeit & Entwicklungspotenziale (Schlüssel-Spannungsaspekte wie Quadrate/Oppositionen, Saturn und Chiron).
5. Höhere Berufung & Schicksalsaufgabe (MC, Mondknoten-Achse).
Beziehe die Zusatzanalysen ein (Aspektfiguren, klassische Würden und Herrscherketten, Horoskopform, Fixsterne, Halbsummenbilder), soweit sie für das Verständnis wesentlich sind.

Schreibe respektvoll, ermutigend, nicht-fatalistisch und formatiere mit klaren Markdown-Überschriften und prägnanten Absätzen.""",

    "beruf": """Erstelle ein professionelles Berufungs- und Karriereprofil für dieses Horoskop:
Analysiere gezielt:
1. Das Medium Coeli (MC) und das 10. Haus (Lebensziel, gesellschaftliche Rolle, Karrierearchetyp).
2. Das 2. und 6. Haus (Finanzielle Talente, Werte, Arbeitsstil und Alltagskompetenz).
3. Merkur, Mars, Sonne und Saturn (Entscheidungskraft, Durchsetzungsvermögen, Disziplin).
4. Konkrete Berufsfelder und Tätigkeitsformen, die dieser astrologischen Signatur entsprechen.""",

    "partnerschaft": """Erstelle eine tiefgründige Partnerschafts- und Beziehungsanalyse für dieses Horoskop:
Analysiere:
1. Den Deszendenten (DC) und das 7. Haus (Das Du, Beziehungserwartungen und Partnerwahl).
2. Venus und Mars (Liebessprache, Sinnlichkeit, Leidenschaft und Anziehungskraft).
3. Den Mond (Bedürfnis nach Nähe vs. Distanz, emotionale Sicherheit).
4. Beziehungsfallen, Projektionen und wie erfüllende Partnerschaft gelingt.""",

    "seelenleben": """Analysiere das seelische Fundament und die emotionale Tiefenpsychologie:
Untersuche:
1. Mond in Zeichen und Haus: Die innere Kind-Wunde, emotionale Reaktionsmuster.
2. Das 4. Haus (Imum Coeli / IC): Herkunft, familiäre Prägungen und seelischer Rückzugsort.
3. Wasser-Betonung und Aspekte von Neptun und Pluto zur Gefühlswelt.""",

    "karma": """Erstelle eine Analyse zu Karma, Seelenplan und Schattenarbeit:
Untersuche:
1. Die Mondknoten-Achse (Absteigender Knoten = vertrautes Altes; Aufsteigender Knoten = seelische Entwicklungsrichtung).
2. Saturn als Meister der Zeit und Hüter der Schwelle (Lebensprüfungen und Reifung).
3. Chiron (Die verwundete Heiler-Wunde) und Lilith (Verdrängte Autonomie).""",

    "transite": """Erstelle eine präzise Transitanalyse (Jahresprognose & Zeitqualität) basierend auf den aktuellen Planetenständen im Verhältnis zum Radix:
1. Die übergeordneten Zeitströmungen durch die Langsamläufer (Pluto, Neptun, Uranus, Saturn).
2. Aktuelle Wendepunkte und Reifephasen durch Jupiter und Mars.
3. Konkrete Lebensbereiche, die jetzt aktiviert werden, und wie diese Energie konstruktiv genutzt werden kann.""",

    "synastrie": """Erstelle eine differenzierte Partnervergleichs- und Synastrie-Analyse zwischen Person A und Person B:
1. Die grundlegende chemische Resonanz (Sonne-Mond, Venus-Mars).
2. Geistiger Austausch und Kommunikation (Merkur-Aspekte).
3. Bindungssicherheit, Loyalität und Beständigkeit (Saturn-Kontakte).
4. Reibungsflächen, Wachstumschancen und das gemeinsame Potenzial der Verbindung.
5. Das Composite- und Davison-Horoskop als Bild der Beziehung selbst (Aszendent, Sonne, Mond, Venus, Saturn im Composite).""",

    "progression": """Deute die Progression (bzw. Solarbogen-Direktion) im Verhältnis zum Radix:
1. Die Entwicklungsphase des Lebens: progressive Sonne (Zeichen/Haus), progressiver Mond und progressive Mondphase.
2. Wechsel von Zeichen oder Haus bei Sonne/Mond/Aszendent/MC und was das bedeutet.
3. Die engsten Aspekte der Progression zum Radix – was wird gerade aktiviert, was reift heran?
4. Praktische Hinweise für die kommenden ein bis zwei Jahre.""",

    "solarreturn": """Deute das Return-Horoskop (z. B. Solar-/Lunar-Return) im Verhältnis zum Radix:
1. Aszendent und MC des Returns und die Stimmung des Zeitabschnitts.
2. Betonte Häuser und Planeten im Return; Aspekte des Returns zum Radix.
3. Chancen, Herausforderungen und Schwerpunkte dieses Zeitraums.""",

    "vedisch": """Erstelle eine vedische (Jyotish-)Deutung auf Grundlage der siderischen Daten:
1. Lagna, Mond-Nakshatra und Pada: Grundcharakter und seelische Prägung.
2. Stärke der Grahas (Erhöhung, eigenes Zeichen, Schwächung), wichtige Hausherren und Yoga-artige Konstellationen.
3. Die Navamsa (D9) als Hinweis auf innere Stärke und Partnerschaft.
4. Die laufende Vimshottari-Dasha/Antardasha: Themen und Zeitqualität.
Verwende Sanskrit-Begriffe mit deutscher Erklärung.""",

    "astrokarte": """Deute die Astrokartografie dieses Geburtshoroskops:
1. Was bedeuten MC-, IC-, Aszendent- und Deszendent-Linien der Planeten allgemein (Beruf, Heimat, Selbstausdruck, Beziehungen)?
2. Analysiere die genannten Orte nahe Planetenlinien: Für welche Lebensthemen sind sie förderlich, wo sind Herausforderungen zu erwarten?
3. Gib besonnene Hinweise, wie man solche Orte nutzen oder meiden kann, ohne fatalistisch zu sein.""",
}

MODULE_NEEDS = {
    "transite": "transit", "synastrie": "partner", "progression": "progression", "solarreturn": "return",
    "vedisch": "vedic", "astrokarte": "astromap",
}


# ========================================================
# QThread Worker für asynchrone KI-Generierung (mit Streaming)
# ========================================================

class AiGenerationWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    chunk_signal = pyqtSignal(str)

    def __init__(self, chart_data, module_key, cfg, extras=None, language="de"):
        super().__init__()
        self.chart_data = chart_data
        self.module_key = module_key
        self.cfg = cfg
        self.extras = extras or {}
        self.language = language
        self._is_cancelled = False
        self._proc = None
        self._response = None
        self._parts = []

    def cancel(self):
        """Bricht ab: laufende CLI-Prozesse und HTTP-Verbindungen werden beendet."""
        self._is_cancelled = True
        proc = self._proc
        if proc is not None and proc.poll() is None:
            self._kill_process_group(proc)
        resp = self._response
        if resp is not None:
            try:
                resp.close()
            except Exception:
                pass

    @staticmethod
    def _kill_process_group(proc):
        """Beendet den CLI-Prozess samt Kindprozessen (Node/Shell-Wrapper halten sonst die Pipe offen)."""
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                proc.kill()
            except OSError:
                pass

    def _emit(self, text):
        if text and not self._is_cancelled:
            self._parts.append(text)
            self.chunk_signal.emit(text)

    def build_prompt(self):
        astro_info = format_astrology_data(self.chart_data, self.extras)
        instruction = MODULE_PROMPTS.get(self.module_key, MODULE_PROMPTS["gesamt"])
        lang_line = (
            "Formuliere deine Deutung in deutscher Sprache mit ansprechender Markdown-Formatierung."
            if self.language != "en" else
            "Write the interpretation in English with clear Markdown formatting (the data below is in German; translate terms naturally)."
        )
        return (
            f"Du bist ein renommierter Meister der psychologischen und klassischen Astrologie.\n\n"
            f"{instruction}\n\n"
            f"Hier sind die exakten Berechnungsdaten (Swiss Ephemeris):\n"
            f"====================================================\n"
            f"{astro_info}\n"
            f"====================================================\n\n"
            f"{lang_line}"
        )

    def run(self):
        try:
            self.status_signal.emit("Bereite astrologische Konstellationsdaten vor...")
            full_prompt = self.build_prompt()
            provider = self.cfg.get("active_provider", "auto")

            if provider == "auto":
                env = detect_environment()
                if env["claude_cli"]:
                    provider = "claude_cli"
                elif env["codex_cli"]:
                    provider = "codex_cli"
                elif env["ollama_running"]:
                    provider = "ollama"
                elif self.cfg.get("api_keys", {}).get("anthropic"):
                    provider = "anthropic"
                elif self.cfg.get("api_keys", {}).get("openai"):
                    provider = "openai"
                elif self.cfg.get("api_keys", {}).get("gemini"):
                    provider = "gemini"
                else:
                    provider = "ollama"

            self.status_signal.emit(f"Sende Anfrage an KI-Provider ({provider})...")

            if provider == "claude_cli":
                self._run_claude_cli(full_prompt)
            elif provider == "codex_cli":
                self._run_codex_cli(full_prompt)
            elif provider == "ollama":
                self._run_ollama(full_prompt)
            elif provider == "anthropic":
                self._run_anthropic_api(full_prompt)
            elif provider == "openai":
                self._run_openai_api(full_prompt)
            elif provider == "gemini":
                self._run_gemini_api(full_prompt)
            elif provider in ("openrouter", "deepseek", "custom"):
                self._run_custom_api(full_prompt, provider)
            else:
                raise ValueError(f"Unbekannter Provider: {provider}")

            if self._is_cancelled:
                return
            res = "".join(self._parts)
            if not res.strip():
                raise RuntimeError("Der KI-Provider hat eine leere Antwort geliefert.")
            self.finished_signal.emit(res)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))

    # ── CLI ──
    def _run_cli(self, binary, args, label):
        self.status_signal.emit(f"{label} generiert Deutung...")
        # Drain stdout without waiting for a newline; stderr goes to a file so
        # a noisy CLI cannot fill its pipe and deadlock generation.
        with tempfile.TemporaryFile() as errors, selectors.DefaultSelector() as selector:
            self._proc = subprocess.Popen(
                [binary, *args], stdout=subprocess.PIPE, stderr=errors, start_new_session=True,
            )
            proc = self._proc
            decoder = codecs.getincrementaldecoder("utf-8")("replace")
            deadline = time.monotonic() + 600
            selector.register(proc.stdout, selectors.EVENT_READ)
            try:
                while selector.get_map():
                    if self._is_cancelled:
                        self._kill_process_group(proc)
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError(f"{label} hat nach 10 Minuten nicht geantwortet.")
                    for key, _ in selector.select(0.1):
                        chunk = os.read(key.fileobj.fileno(), 16384)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            self._emit(decoder.decode(chunk))
                self._emit(decoder.decode(b"", final=True))
                proc.wait(timeout=max(0.1, deadline - time.monotonic()))
                returncode = proc.returncode
                errors.seek(0)
                stderr = errors.read(16384).decode("utf-8", errors="replace")
            finally:
                if proc.poll() is None:
                    self._kill_process_group(proc)
                proc.wait()
                proc.stdout.close()
                self._proc = None
        if self._is_cancelled:
            return
        if returncode != 0:
            raise RuntimeError(f"{label} Fehler ({returncode}): {stderr.strip() or ''.join(self._parts).strip()}")

    def _run_claude_cli(self, prompt):
        claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
        if not os.path.exists(claude_bin):
            raise FileNotFoundError("Claude CLI nicht gefunden unter ~/.local/bin/claude oder PATH.")
        self._run_cli(claude_bin, ["-p", prompt], "Claude CLI")

    def _run_codex_cli(self, prompt):
        codex_bin = shutil.which("codex") or os.path.expanduser("~/.local/bin/codex")
        if not os.path.exists(codex_bin):
            raise FileNotFoundError("Codex CLI nicht gefunden unter ~/.local/bin/codex oder PATH.")
        self._run_cli(codex_bin, ["exec", prompt], "Codex CLI")

    # ── HTTP ──
    def _open(self, url, payload, headers=None, timeout=300):
        all_headers = {"Content-Type": "application/json"}
        all_headers.update(headers or {})
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=all_headers)
        try:
            self._response = urllib.request.urlopen(req, timeout=timeout)
            return self._response
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:600]
            except Exception:
                pass
            raise RuntimeError(f"HTTP {e.code} von {urllib.parse.urlparse(url).netloc}: {body or e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Verbindung zu {urllib.parse.urlparse(url).netloc} fehlgeschlagen: {e.reason}")

    def _stream_sse(self, url, payload, headers, extract, timeout=300):
        """Server-Sent Events: `data: {json}`-Zeilen; extract(obj) → Text oder None."""
        resp = self._open(url, payload, headers, timeout)
        try:
            for raw in resp:
                if self._is_cancelled:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                self._emit(extract(obj))
        finally:
            try:
                resp.close()
            except Exception:
                pass
            self._response = None

    def _run_ollama(self, prompt):
        base = self.cfg.get("ollama_url", "http://127.0.0.1:11434").rstrip("/")
        model = self.cfg.get("ollama_model", "mistral")
        # Ist das eingestellte Modell nicht installiert, nimmt Ollama-Auto-Detect das erste vorhandene.
        try:
            installed = detect_environment()["ollama_models"] if base.endswith(":11434") else []
        except Exception:
            installed = []
        if installed and model not in installed and f"{model}:latest" not in installed:
            model = installed[0]
            self.status_signal.emit(f"Eingestelltes Modell fehlt, nutze {model}...")
        resp = self._open(base + "/api/generate", {"model": model, "prompt": prompt, "stream": True}, timeout=600)
        try:
            for raw in resp:
                if self._is_cancelled:
                    break
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except ValueError:
                    continue
                self._emit(obj.get("response", ""))
                if obj.get("done"):
                    break
        finally:
            try:
                resp.close()
            except Exception:
                pass
            self._response = None

    def _run_anthropic_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("anthropic")
        if not key:
            raise ValueError("Kein Anthropic API-Schlüssel hinterlegt.")
        model = self.cfg.get("models", {}).get("anthropic", "claude-sonnet-5-5")

        def extract(obj):
            if obj.get("type") == "content_block_delta":
                return obj.get("delta", {}).get("text", "")
            if obj.get("type") == "error":
                raise RuntimeError(obj.get("error", {}).get("message", "API-Fehler"))
            return None

        self._stream_sse(
            "https://api.anthropic.com/v1/messages",
            {"model": model, "max_tokens": 4096, "stream": True, "messages": [{"role": "user", "content": prompt}]},
            {"x-api-key": key, "anthropic-version": "2023-06-01"}, extract, 300)

    def _openai_like(self, url, headers, model, prompt):
        def extract(obj):
            if obj.get("error"):
                err = obj["error"]
                raise RuntimeError(err.get("message", str(err)) if isinstance(err, dict) else str(err))
            ch = (obj.get("choices") or [{}])[0]
            return (ch.get("delta") or {}).get("content", "")

        self._stream_sse(url, {"model": model, "stream": True, "temperature": 0.7,
                               "messages": [{"role": "user", "content": prompt}]}, headers, extract, 300)

    def _run_openai_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("openai")
        if not key:
            raise ValueError("Kein OpenAI API-Schlüssel hinterlegt.")
        model = self.cfg.get("models", {}).get("openai", "gpt-4o")
        self._openai_like("https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {key}"}, model, prompt)

    def _run_gemini_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("gemini")
        if not key:
            raise ValueError("Kein Google Gemini API-Schlüssel hinterlegt.")
        model = self.cfg.get("models", {}).get("gemini", "gemini-2.5-pro")

        def extract(obj):
            parts = ((obj.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts)

        # Schlüssel im Header statt in der URL: URLs landen in Logs und Fehlermeldungen.
        self._stream_sse(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse",
            {"contents": [{"parts": [{"text": prompt}]}]}, {"x-goog-api-key": key}, extract, 300)

    def _run_custom_api(self, prompt, provider_name):
        key = self.cfg.get("api_keys", {}).get(provider_name, "")
        if provider_name == "openrouter":
            url = "https://openrouter.ai/api/v1/chat/completions"
            model = self.cfg.get("models", {}).get("openrouter", "deepseek/deepseek-chat")
        elif provider_name == "deepseek":
            url = "https://api.deepseek.com/chat/completions"
            model = self.cfg.get("models", {}).get("deepseek", "deepseek-chat")
        else:
            url = self.cfg.get("custom_url", "http://127.0.0.1:1234/v1").rstrip("/") + "/chat/completions"
            model = self.cfg.get("custom_model", "local-model")
        self._openai_like(url, {"Authorization": f"Bearer {key}"} if key else {}, model, prompt)
