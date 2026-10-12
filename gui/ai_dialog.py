# -*- coding: utf-8 -*-
"""
Astrorust — KI-Einstellungen Dialog (Breeze Dark / LME Stil)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QGroupBox, QMessageBox
)

from ai_engine import AiConfig, detect_environment
import styles


class AiSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KI-Deutung Einstellungen")
        self.setMinimumWidth(560)
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
        self.combo_provider.addItem("Automatische Erkennung (Auto-Detect)", "auto")
        if self.env["claude_cli"]:
            self.combo_provider.addItem("⚡ Claude Code CLI (Lokal ohne Key)", "claude_cli")
        if self.env["codex_cli"]:
            self.combo_provider.addItem("⚡ Codex CLI (Lokal)", "codex_cli")
        self.combo_provider.addItem("🦙 Ollama (Lokal)", "ollama")
        self.combo_provider.addItem("🔑 Anthropic (Claude API)", "anthropic")
        self.combo_provider.addItem("🔑 OpenAI (GPT-4o API)", "openai")
        self.combo_provider.addItem("🔑 Google Gemini API", "gemini")
        self.combo_provider.addItem("🔑 OpenRouter API", "openrouter")
        self.combo_provider.addItem("🔑 DeepSeek API", "deepseek")
        self.combo_provider.addItem("🌐 Eigener Endpoint (OpenAI-kompatibel)", "custom")

        l_prov.addWidget(self.combo_provider, 0, 1)

        btn_import_genoffice = QPushButton("📥 Aus GenOffice importieren")
        btn_import_genoffice.setToolTip("Übernimmt gespeicherte API-Keys und Modelle aus ~/.config/GenOffice/ai-settings.json")
        btn_import_genoffice.clicked.connect(self._import_genoffice)
        l_prov.addWidget(btn_import_genoffice, 0, 2)

        layout.addWidget(box_prov)

        # 3. API-Schlüssel
        box_keys = QGroupBox("API-Schlüssel (Direktzugriff)")
        l_keys = QGridLayout(box_keys)
        l_keys.setSpacing(6)

        l_keys.addWidget(QLabel("Anthropic API-Key:"), 0, 0)
        self.edit_key_anthropic = QLineEdit()
        self.edit_key_anthropic.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key_anthropic.setPlaceholderText("sk-ant-...")
        l_keys.addWidget(self.edit_key_anthropic, 0, 1)

        l_keys.addWidget(QLabel("OpenAI API-Key:"), 1, 0)
        self.edit_key_openai = QLineEdit()
        self.edit_key_openai.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key_openai.setPlaceholderText("sk-proj-...")
        l_keys.addWidget(self.edit_key_openai, 1, 1)

        l_keys.addWidget(QLabel("Gemini API-Key:"), 2, 0)
        self.edit_key_gemini = QLineEdit()
        self.edit_key_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key_gemini.setPlaceholderText("AIzaSy...")
        l_keys.addWidget(self.edit_key_gemini, 2, 1)

        l_keys.addWidget(QLabel("OpenRouter / DeepSeek:"), 3, 0)
        self.edit_key_openrouter = QLineEdit()
        self.edit_key_openrouter.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key_openrouter.setPlaceholderText("sk-or-...")
        l_keys.addWidget(self.edit_key_openrouter, 3, 1)

        layout.addWidget(box_keys)

        # 4. Lokale / Eigene Server URLs
        box_endpoints = QGroupBox("Lokale Endpoints")
        l_end = QGridLayout(box_endpoints)

        l_end.addWidget(QLabel("Ollama URL & Modell:"), 0, 0)
        self.edit_ollama_url = QLineEdit()
        self.edit_ollama_model = QLineEdit()
        l_end.addWidget(self.edit_ollama_url, 0, 1)
        l_end.addWidget(self.edit_ollama_model, 0, 2)

        l_end.addWidget(QLabel("Custom URL & Modell:"), 1, 0)
        self.edit_custom_url = QLineEdit()
        self.edit_custom_model = QLineEdit()
        l_end.addWidget(self.edit_custom_url, 1, 1)
        l_end.addWidget(self.edit_custom_model, 1, 2)

        layout.addWidget(box_endpoints)

        # 5. Buttons
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

    def _load_values(self):
        prov = self.cfg.get("active_provider", "auto")
        idx = self.combo_provider.findData(prov)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)

        keys = self.cfg.get("api_keys", {})
        self.edit_key_anthropic.setText(keys.get("anthropic", ""))
        self.edit_key_openai.setText(keys.get("openai", ""))
        self.edit_key_gemini.setText(keys.get("gemini", ""))
        self.edit_key_openrouter.setText(keys.get("openrouter", "") or keys.get("deepseek", ""))

        self.edit_ollama_url.setText(self.cfg.get("ollama_url", "http://127.0.0.1:11434"))
        self.edit_ollama_model.setText(self.cfg.get("ollama_model", "mistral"))
        self.edit_custom_url.setText(self.cfg.get("custom_url", "http://127.0.0.1:1234/v1"))
        self.edit_custom_model.setText(self.cfg.get("custom_model", "local-model"))

    def _import_genoffice(self):
        count = AiConfig.import_from_genoffice(self.cfg)
        if count > 0:
            self._load_values()
            QMessageBox.information(
                self, "Import erfolgreich",
                f"{count} API-Schlüssel & Modell-Einstellungen wurden erfolgreich aus GenOffice übernommen!"
            )
        else:
            QMessageBox.warning(
                self, "GenOffice Import",
                "In ~/.config/GenOffice/ai-settings.json wurden keine hinterlegten API-Schlüssel gefunden."
            )

    def _save_and_close(self):
        self.cfg["active_provider"] = self.combo_provider.currentData()
        self.cfg["api_keys"]["anthropic"] = self.edit_key_anthropic.text().strip()
        self.cfg["api_keys"]["openai"] = self.edit_key_openai.text().strip()
        self.cfg["api_keys"]["gemini"] = self.edit_key_gemini.text().strip()
        self.cfg["api_keys"]["openrouter"] = self.edit_key_openrouter.text().strip()
        self.cfg["api_keys"]["deepseek"] = self.edit_key_openrouter.text().strip()

        self.cfg["ollama_url"] = self.edit_ollama_url.text().strip()
        self.cfg["ollama_model"] = self.edit_ollama_model.text().strip()
        self.cfg["custom_url"] = self.edit_custom_url.text().strip()
        self.cfg["custom_model"] = self.edit_custom_model.text().strip()

        AiConfig.save(self.cfg)
        self.accept()
