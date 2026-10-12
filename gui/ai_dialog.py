# -*- coding: utf-8 -*-
"""
Astrorust — KI-Einstellungen Dialog (Breeze Dark / LME Stil)
Bring-Your-Own-Key (BYOK) Architektur für alle gängigen KI-Provider und lokale LLMs.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QGroupBox, QTabWidget, QWidget, QMessageBox
)

from ai_engine import AiConfig, detect_environment
import styles


class AiSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KI-Deutung — Provider & API-Keys")
        self.setMinimumWidth(620)
        self.setStyleSheet(styles.DARK_STYLESHEET)

        self.cfg = AiConfig.load()
        self.env = detect_environment()

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        # 1. Erkannte lokale KI-Agenten Infobox
        box_detected = QGroupBox("Erkannte lokale KI-Dienste")
        l_det = QVBoxLayout(box_detected)

        claude_status = "✔ Gefunden (~/.local/bin/claude)" if self.env["claude_cli"] else "✘ Nicht im Pfad"
        codex_status = "✔ Gefunden (~/.local/bin/codex)" if self.env["codex_cli"] else "✘ Nicht im Pfad"
        ollama_status = f"✔ Aktiv ({len(self.env['ollama_models'])} Modelle)" if self.env["ollama_running"] else "✘ Nicht erreichbar (Port 11434)"

        lbl_claude = QLabel(f"<b>Claude Code CLI:</b> {claude_status}")
        lbl_codex = QLabel(f"<b>Codex CLI:</b> {codex_status}")
        lbl_ollama = QLabel(f"<b>Ollama (Lokal):</b> {ollama_status}")

        lbl_claude.setStyleSheet(f"color: {styles.START_GREEN if self.env['claude_cli'] else styles.TEXT_MUTED};")
        lbl_codex.setStyleSheet(f"color: {styles.START_GREEN if self.env['codex_cli'] else styles.TEXT_MUTED};")
        lbl_ollama.setStyleSheet(f"color: {styles.START_GREEN if self.env['ollama_running'] else styles.TEXT_MUTED};")

        l_det.addWidget(lbl_claude)
        l_det.addWidget(lbl_codex)
        l_det.addWidget(lbl_ollama)
        layout.addWidget(box_detected)

        # 2. Provider Auswahl
        box_prov = QGroupBox("Aktiver Provider")
        l_prov = QGridLayout(box_prov)
        l_prov.setSpacing(8)

        l_prov.addWidget(QLabel("Bevorzugter Dienst:"), 0, 0)
        self.combo_provider = QComboBox()
        self.combo_provider.addItem("Automatische Erkennung (Auto-Detect: Lokale CLIs > API-Keys)", "auto")
        if self.env["claude_cli"]:
            self.combo_provider.addItem("⚡ Claude Code CLI (Lokal ohne Key)", "claude_cli")
        if self.env["codex_cli"]:
            self.combo_provider.addItem("⚡ Codex CLI (Lokal)", "codex_cli")
        self.combo_provider.addItem("🦙 Ollama (Lokal)", "ollama")
        self.combo_provider.addItem("🔑 Google Gemini API", "gemini")
        self.combo_provider.addItem("🔑 Anthropic (Claude API)", "anthropic")
        self.combo_provider.addItem("🔑 OpenAI (GPT API)", "openai")
        self.combo_provider.addItem("🔑 DeepSeek API", "deepseek")
        self.combo_provider.addItem("🔑 OpenRouter API", "openrouter")
        self.combo_provider.addItem("🌐 Eigener Endpoint (OpenAI-kompatibel / LM Studio / vLLM)", "custom")

        l_prov.addWidget(self.combo_provider, 0, 1)
        layout.addWidget(box_prov)

        # 3. Provider Konfiguration (Tabs: Cloud Provider & Lokale Server)
        tab_widget = QTabWidget()

        # Tab Cloud Providers
        tab_cloud = QWidget()
        l_cloud = QGridLayout(tab_cloud)
        l_cloud.setSpacing(10)

        # Header
        l_cloud.addWidget(QLabel("<b>Provider</b>"), 0, 0)
        l_cloud.addWidget(QLabel("<b>API-Key</b>"), 0, 1)
        l_cloud.addWidget(QLabel("<b>Modell</b>"), 0, 2)

        # Google Gemini
        l_cloud.addWidget(QLabel("Google Gemini:"), 1, 0)
        self.edit_key_gemini = self._create_password_edit("AIzaSy...")
        self.edit_model_gemini = QLineEdit()
        self.edit_model_gemini.setPlaceholderText("gemini-2.5-pro")
        l_cloud.addLayout(self.edit_key_gemini["layout"], 1, 1)
        l_cloud.addWidget(self.edit_model_gemini, 1, 2)

        # Anthropic Claude
        l_cloud.addWidget(QLabel("Anthropic (Claude):"), 2, 0)
        self.edit_key_anthropic = self._create_password_edit("sk-ant-...")
        self.edit_model_anthropic = QLineEdit()
        self.edit_model_anthropic.setPlaceholderText("claude-sonnet-5-5")
        l_cloud.addLayout(self.edit_key_anthropic["layout"], 2, 1)
        l_cloud.addWidget(self.edit_model_anthropic, 2, 2)

        # OpenAI
        l_cloud.addWidget(QLabel("OpenAI (GPT):"), 3, 0)
        self.edit_key_openai = self._create_password_edit("sk-proj-...")
        self.edit_model_openai = QLineEdit()
        self.edit_model_openai.setPlaceholderText("gpt-4o")
        l_cloud.addLayout(self.edit_key_openai["layout"], 3, 1)
        l_cloud.addWidget(self.edit_model_openai, 3, 2)

        # DeepSeek
        l_cloud.addWidget(QLabel("DeepSeek:"), 4, 0)
        self.edit_key_deepseek = self._create_password_edit("sk-...")
        self.edit_model_deepseek = QLineEdit()
        self.edit_model_deepseek.setPlaceholderText("deepseek-chat")
        l_cloud.addLayout(self.edit_key_deepseek["layout"], 4, 1)
        l_cloud.addWidget(self.edit_model_deepseek, 4, 2)

        # OpenRouter
        l_cloud.addWidget(QLabel("OpenRouter:"), 5, 0)
        self.edit_key_openrouter = self._create_password_edit("sk-or-...")
        self.edit_model_openrouter = QLineEdit()
        self.edit_model_openrouter.setPlaceholderText("deepseek/deepseek-chat")
        l_cloud.addLayout(self.edit_key_openrouter["layout"], 5, 1)
        l_cloud.addWidget(self.edit_model_openrouter, 5, 2)

        tab_widget.addTab(tab_cloud, "🔑 Cloud API-Keys")

        # Tab Lokale Server
        tab_local = QWidget()
        l_local = QGridLayout(tab_local)
        l_local.setSpacing(10)

        l_local.addWidget(QLabel("<b>Dienst</b>"), 0, 0)
        l_local.addWidget(QLabel("<b>Server-URL</b>"), 0, 1)
        l_local.addWidget(QLabel("<b>Modell</b>"), 0, 2)

        l_local.addWidget(QLabel("Ollama:"), 1, 0)
        self.edit_ollama_url = QLineEdit()
        self.edit_ollama_model = QLineEdit()
        l_local.addWidget(self.edit_ollama_url, 1, 1)
        l_local.addWidget(self.edit_ollama_model, 1, 2)

        l_local.addWidget(QLabel("Custom Endpoint:"), 2, 0)
        self.edit_custom_url = QLineEdit()
        self.edit_custom_model = QLineEdit()
        l_local.addWidget(self.edit_custom_url, 2, 1)
        l_local.addWidget(self.edit_custom_model, 2, 2)

        tab_widget.addTab(tab_local, "🌐 Lokale Server / Ollama")
        layout.addWidget(tab_widget)

        # 4. Buttons
        h_btn = QHBoxLayout()
        h_btn.addStretch()

        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.clicked.connect(self.reject)
        h_btn.addWidget(btn_cancel)

        btn_save = QPushButton("Speichern & Schließen")
        btn_save.setObjectName("btn_start")
        btn_save.clicked.connect(self._save_and_close)
        h_btn.addWidget(btn_save)

        layout.addLayout(h_btn)

    def _create_password_edit(self, placeholder=""):
        h_box = QHBoxLayout()
        h_box.setContentsMargins(0, 0, 0, 0)
        h_box.setSpacing(4)

        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setPlaceholderText(placeholder)

        btn_toggle = QPushButton("👁")
        btn_toggle.setFixedWidth(30)
        btn_toggle.setToolTip("Passwort anzeigen/verbergen")

        def toggle():
            if edit.echoMode() == QLineEdit.EchoMode.Password:
                edit.setEchoMode(QLineEdit.EchoMode.Normal)
                btn_toggle.setText("🔒")
            else:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                btn_toggle.setText("👁")

        btn_toggle.clicked.connect(toggle)
        h_box.addWidget(edit)
        h_box.addWidget(btn_toggle)

        return {"layout": h_box, "edit": edit, "btn": btn_toggle}

    def _load_values(self):
        prov = self.cfg.get("active_provider", "auto")
        idx = self.combo_provider.findData(prov)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)

        keys = self.cfg.get("api_keys", {})
        models = self.cfg.get("models", {})

        self.edit_key_gemini["edit"].setText(keys.get("gemini", ""))
        self.edit_key_anthropic["edit"].setText(keys.get("anthropic", ""))
        self.edit_key_openai["edit"].setText(keys.get("openai", ""))
        self.edit_key_deepseek["edit"].setText(keys.get("deepseek", ""))
        self.edit_key_openrouter["edit"].setText(keys.get("openrouter", ""))

        self.edit_model_gemini.setText(models.get("gemini", "gemini-2.5-pro"))
        self.edit_model_anthropic.setText(models.get("anthropic", "claude-sonnet-5-5"))
        self.edit_model_openai.setText(models.get("openai", "gpt-4o"))
        self.edit_model_deepseek.setText(models.get("deepseek", "deepseek-chat"))
        self.edit_model_openrouter.setText(models.get("openrouter", "deepseek/deepseek-chat"))

        self.edit_ollama_url.setText(self.cfg.get("ollama_url", "http://127.0.0.1:11434"))
        self.edit_ollama_model.setText(self.cfg.get("ollama_model", "mistral"))
        self.edit_custom_url.setText(self.cfg.get("custom_url", "http://127.0.0.1:1234/v1"))
        self.edit_custom_model.setText(self.cfg.get("custom_model", "local-model"))

    def _save_and_close(self):
        self.cfg["active_provider"] = self.combo_provider.currentData()
        self.cfg.setdefault("api_keys", {})

        # Keys
        self.cfg["api_keys"]["gemini"] = self.edit_key_gemini["edit"].text().strip()
        self.cfg["api_keys"]["anthropic"] = self.edit_key_anthropic["edit"].text().strip()
        self.cfg["api_keys"]["openai"] = self.edit_key_openai["edit"].text().strip()
        self.cfg["api_keys"]["deepseek"] = self.edit_key_deepseek["edit"].text().strip()
        self.cfg["api_keys"]["openrouter"] = self.edit_key_openrouter["edit"].text().strip()

        # Models
        if "models" not in self.cfg:
            self.cfg["models"] = {}
        self.cfg["models"]["gemini"] = self.edit_model_gemini.text().strip() or "gemini-2.5-pro"
        self.cfg["models"]["anthropic"] = self.edit_model_anthropic.text().strip() or "claude-sonnet-5-5"
        self.cfg["models"]["openai"] = self.edit_model_openai.text().strip() or "gpt-4o"
        self.cfg["models"]["deepseek"] = self.edit_model_deepseek.text().strip() or "deepseek-chat"
        self.cfg["models"]["openrouter"] = self.edit_model_openrouter.text().strip() or "deepseek/deepseek-chat"

        # Endpoints
        self.cfg["ollama_url"] = self.edit_ollama_url.text().strip()
        self.cfg["ollama_model"] = self.edit_ollama_model.text().strip()
        self.cfg["custom_url"] = self.edit_custom_url.text().strip()
        self.cfg["custom_model"] = self.edit_custom_model.text().strip()

        AiConfig.save(self.cfg)
        self.accept()
