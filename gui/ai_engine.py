# -*- coding: utf-8 -*-
"""
Astrorust — KI-Deutungsengine (Multi-Provider: Claude CLI, Codex CLI, Ollama, API-Keys, GenOffice-Import)
"""

import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
import ssl
from PyQt6.QtCore import QThread, pyqtSignal

GENOFFICE_SETTINGS_PATH = os.path.expanduser("~/.config/GenOffice/ai-settings.json")
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
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4o",
            "gemini": "gemini-1.5-pro",
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
                    # Merge defaults
                    merged = dict(cls.DEFAULT_CONFIG)
                    merged.update(cfg)
                    return merged
            except Exception as e:
                print("Fehler beim Laden der KI-Einstellungen:", e)

        # First run: try auto-import from GenOffice
        cfg = dict(cls.DEFAULT_CONFIG)
        cls.import_from_genoffice(cfg)
        cls.save(cfg)
        return cfg

    @classmethod
    def save(cls, config_dict):
        os.makedirs(ASTRORUST_CONFIG_DIR, exist_ok=True)
        try:
            with open(ASTRORUST_AI_SETTINGS, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Fehler beim Speichern der KI-Einstellungen:", e)

    @classmethod
    def import_from_genoffice(cls, target_config):
        if not os.path.exists(GENOFFICE_SETTINGS_PATH):
            return 0

        imported = 0
        try:
            with open(GENOFFICE_SETTINGS_PATH, "r", encoding="utf-8") as f:
                go_data = json.load(f)

            providers = go_data.get("providers", {})
            for p_name, p_data in providers.items():
                key = p_data.get("apiKey") or p_data.get("key")
                if key:
                    if p_name in target_config["api_keys"]:
                        target_config["api_keys"][p_name] = key
                        imported += 1
                    elif p_name == "google":
                        target_config["api_keys"]["gemini"] = key
                        imported += 1

                model = p_data.get("model")
                if model and p_name in target_config["models"]:
                    target_config["models"][p_name] = model

        except Exception as e:
            print("Fehler beim Import aus GenOffice:", e)

        return imported


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

def format_astrology_data(chart, transit_chart=None, synastry_chart=None):
    c = chart
    p_lines = []
    for p in c.get("planets", []):
        dig = f", Würde: {p['dignity']}" if p.get("dignity") else ""
        rx = " [RÜCKLÄUFIG ℞]" if p.get("is_retrograde") else ""
        p_lines.append(f"- {p['name']} ({p['glyph']}): {p['formatted_deg']} in {p['sign_name']} (Haus {p['house']}){dig}{rx}")

    h_lines = []
    for h in c.get("houses", []):
        cusp_name = ""
        if h["house_number"] == 1: cusp_name = " (Aszendent / AC)"
        elif h["house_number"] == 10: cusp_name = " (Medium Coeli / MC)"
        elif h["house_number"] == 7: cusp_name = " (Deszendent / DC)"
        elif h["house_number"] == 4: cusp_name = " (Imum Coeli / IC)"
        h_lines.append(f"- Haus {h['house_number']}{cusp_name}: {h['formatted_deg']} in {h['sign_name']}")

    asp_lines = []
    for asp in c.get("aspects", [])[:18]:  # Die wichtigsten Aspekte
        app_str = "applikativ" if asp.get("is_applying") else "separativ"
        asp_lines.append(f"- {asp['point_a_name']} {asp['aspect_name']} {asp['point_b_name']} (Orb: {asp['formatted_orb']}, {app_str}, Winkel: {asp['actual_angle']:.2f}°)")

    eq = c.get("element_quality", {})
    eq_summary = (
        f"Elemente: Feuer={eq.get('fire')}, Erde={eq.get('earth')}, Luft={eq.get('air')}, Wasser={eq.get('water')} "
        f"(Dominant: {eq.get('dominant_element')})\n"
        f"Qualitäten: Kardinal={eq.get('cardinal')}, Fix={eq.get('fixed')}, Veränderlich={eq.get('mutable')} "
        f"(Dominant: {eq.get('dominant_quality')})"
    )

    text = f"""GEBURTSDATUMEN:
Name: {c.get('name')}
Zeitpunkt: {c.get('date_time')}
Ort: {c.get('location_name')} ({c.get('latitude'):.4f}° N/S, {c.get('longitude'):.4f}° E/W)
Häusersystem: {c.get('house_system')}
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

    if transit_chart:
        tr_lines = []
        for p in transit_chart.get("planets", []):
            rx = " [℞]" if p.get("is_retrograde") else ""
            tr_lines.append(f"- Transit-{p['name']}: {p['formatted_deg']} in {p['sign_name']}{rx}")
        text += f"\n\nAKTUELLE TRANSITE:\nZeitpunkt der Transite: {transit_chart.get('date_time')}\n" + "\n".join(tr_lines)

    if synastry_chart:
        syn_lines = []
        for p in synastry_chart.get("planets", []):
            syn_lines.append(f"- {synastry_chart.get('name')} {p['name']}: {p['formatted_deg']} in {p['sign_name']} (Haus {p['house']})")
        text += f"\n\nPARTNER-HOROSKOP ({synastry_chart.get('name')}):\n" + "\n".join(syn_lines)

    return text


MODULE_PROMPTS = {
    "gesamt": """Erstelle eine fundierte, psychologisch tiefgründige Radix-Gesamtanalyse für dieses Geburtshoroskop (im Stil der psychologischen Astrologie von Liz Greene, C.G. Jung und Anita Cortesi / Astroplus).
Strukturiere die Analyse in folgende Kapitel:
1. Der Wesenskern: Synthese aus Sonne, Mond und Aszendent (Das persönliche Dreieck).
2. Seelische Dynamik & emotionale Veranlagung (Mond, 4. Haus, Wasser/Erde-Gewichtung).
3. Geist, Kommunikation & Handlungskraft (Merkur, Mars, Feuer/Luft).
4. Herausforderungen, Schattenarbeit & Entwicklungspotenziale (Schlüssel-Spannungsaspekte wie Quadrate/Oppositionen, Saturn und Chiron).
5. Höhere Berufung & Schicksalsaufgabe (MC, Mondknoten-Achse).

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
4. Reibungsflächen, Wachstumschancen und das gemeinsame Potenzial der Verbindung.""",
}


# ========================================================
# QThread Worker für asynchrone KI-Generierung
# ========================================================

class AiGenerationWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, chart_data, module_key, cfg, transit_chart=None, synastry_chart=None):
        super().__init__()
        self.chart_data = chart_data
        self.module_key = module_key
        self.cfg = cfg
        self.transit_chart = transit_chart
        self.synastry_chart = synastry_chart
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.status_signal.emit("Bereite astrologische Konstellationsdaten vor...")
            astro_info = format_astrology_data(self.chart_data, self.transit_chart, self.synastry_chart)
            instruction = MODULE_PROMPTS.get(self.module_key, MODULE_PROMPTS["gesamt"])

            full_prompt = (
                f"Du bist ein renommierter Meister der psychologischen und klassischen Astrologie.\n\n"
                f"{instruction}\n\n"
                f"Hier sind die exakten Berechnungsdaten (Swiss Ephemeris):\n"
                f"====================================================\n"
                f"{astro_info}\n"
                f"====================================================\n\n"
                f"Formuliere deine Deutung in deutscher Sprache mit ansprechender Markdown-Formatierung."
            )

            provider = self.cfg.get("active_provider", "auto")

            # Auto-Detection
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
                res = self._run_claude_cli(full_prompt)
            elif provider == "codex_cli":
                res = self._run_codex_cli(full_prompt)
            elif provider == "ollama":
                res = self._run_ollama(full_prompt)
            elif provider == "anthropic":
                res = self._run_anthropic_api(full_prompt)
            elif provider == "openai":
                res = self._run_openai_api(full_prompt)
            elif provider == "gemini":
                res = self._run_gemini_api(full_prompt)
            elif provider in ("openrouter", "deepseek", "custom"):
                res = self._run_custom_api(full_prompt, provider)
            else:
                raise ValueError(f"Unbekannter Provider: {provider}")

            if self._is_cancelled:
                return

            self.finished_signal.emit(res)
        except Exception as e:
            if not self._is_cancelled:
                self.error_signal.emit(str(e))

    def _run_claude_cli(self, prompt):
        claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
        if not os.path.exists(claude_bin):
            raise FileNotFoundError("Claude CLI nicht gefunden unter ~/.local/bin/claude oder PATH.")

        self.status_signal.emit("Claude Code generiert Deutung...")
        cmd = [claude_bin, "-p", prompt]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Claude CLI Fehler ({proc.returncode}): {stderr.strip() or stdout.strip()}")
        return stdout.strip()

    def _run_codex_cli(self, prompt):
        codex_bin = shutil.which("codex") or os.path.expanduser("~/.local/bin/codex")
        if not os.path.exists(codex_bin):
            raise FileNotFoundError("Codex CLI nicht gefunden unter ~/.local/bin/codex oder PATH.")

        self.status_signal.emit("Codex CLI generiert Deutung...")
        cmd = [codex_bin, "exec", prompt]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"Codex CLI Fehler ({proc.returncode}): {stderr.strip() or stdout.strip()}")
        return stdout.strip()

    def _run_ollama(self, prompt):
        url = self.cfg.get("ollama_url", "http://127.0.0.1:11434").rstrip("/") + "/api/generate"
        model = self.cfg.get("ollama_model", "mistral")
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "")

    def _run_anthropic_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("anthropic")
        if not key:
            raise ValueError("Kein Anthropic API-Schlüssel hinterlegt.")

        model = self.cfg.get("models", {}).get("anthropic", "claude-3-5-sonnet-20241022")
        url = "https://api.anthropic.com/v1/messages"
        payload = json.dumps({
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        }
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("content", [{}])[0].get("text", "")

    def _run_openai_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("openai")
        if not key:
            raise ValueError("Kein OpenAI API-Schlüssel hinterlegt.")

        model = self.cfg.get("models", {}).get("openai", "gpt-4o")
        url = "https://api.openai.com/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _run_gemini_api(self, prompt):
        key = self.cfg.get("api_keys", {}).get("gemini")
        if not key:
            raise ValueError("Kein Google Gemini API-Schlüssel hinterlegt.")

        model = self.cfg.get("models", {}).get("gemini", "gemini-1.5-pro")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

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

        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }).encode("utf-8")

        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
