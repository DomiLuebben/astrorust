# -*- coding: utf-8 -*-
"""
Astrorust — Hauptfenster: Menüs, Werkzeugleiste, beliebig viele Horoskop-Tabs (ChartView).
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QPushButton, QMessageBox, QApplication, QLabel,
)

import styles
from appsettings import AppSettings
from chartview import ChartView, EINSTEIN_DEFAULT
from database_dialog import DatabaseDialog
from i18n import tr
from profilestore import ProfileStore
from rust_backend import RustBackend
from settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings | None = None):
        super().__init__()
        self.setWindowTitle(tr("Astrorust — Professionelle Horoskopie & Ephemeriden"))
        self.setMinimumSize(QSize(1260, 800))

        self.backend = RustBackend.get()
        self.settings = settings or AppSettings.load()
        self.store = ProfileStore(self.backend)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

        self._create_menus()
        self._create_toolbar()
        self._update_status_hint()

        first = self.add_tab(None, calculate=False)
        first.calculate()

    # ─────────────────────── Tabs ───────────────────────
    def current(self) -> ChartView | None:
        w = self.tabs.currentWidget()
        return w if isinstance(w, ChartView) else None

    def add_tab(self, profile=None, calculate=True) -> ChartView:
        view = ChartView(self.backend, self.settings, self.store, profile or EINSTEIN_DEFAULT)
        idx = self.tabs.addTab(view, (profile or EINSTEIN_DEFAULT).get("name", tr("Horoskop")))
        self.tabs.setCurrentIndex(idx)
        view.titleChanged.connect(lambda name, v=view: self._set_tab_title(v, name))
        view.statusMessage.connect(lambda msg: self.statusBar().showMessage(msg, 8000))
        view.openDatabase.connect(self.open_database)
        if calculate:
            view.calculate()
        return view

    def new_tab(self):
        cur = self.current()
        profile = cur.person_a.profile() if cur else dict(EINSTEIN_DEFAULT)
        profile["name"] = tr("Neues Horoskop")
        self.add_tab(profile, calculate=False)

    def _set_tab_title(self, view, name):
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabText(i, name or tr("Horoskop"))

    def close_tab(self, index):
        w = self.tabs.widget(index)
        if self.tabs.count() <= 1:
            return
        if isinstance(w, ChartView):
            w.shutdown()
        self.tabs.removeTab(index)
        w.deleteLater()

    def _on_tab_changed(self, _):
        v = self.current()
        if v:
            v.refresh_profiles()

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, ChartView):
                w.shutdown()
        super().closeEvent(event)

    # ─────────────────────── Menüs ───────────────────────
    def _act(self, menu, text, slot, shortcut=None):
        a = QAction(text, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(lambda checked=False: slot())
        menu.addAction(a)
        return a

    def _on_current(self, method, *args):
        def run():
            v = self.current()
            if v:
                getattr(v, method)(*args)
        return run

    def _create_menus(self):
        mb = self.menuBar()
        m = mb.addMenu(tr("&Datei"))
        self._act(m, tr("&Neues Horoskop (Tab)"), self.new_tab, "Ctrl+T")
        self._act(m, tr("&Horoskop berechnen"), self._on_current("calculate"), "F5")
        self._act(m, tr("&Jetzt (Live)"), self._on_current("set_now"), "F6")
        self._act(m, tr("Tab &schließen"), lambda: self.close_tab(self.tabs.currentIndex()), "Ctrl+W")
        m.addSeparator()
        self._act(m, tr("Als &SVG-Vektorgrafik exportieren…"), self._on_current("export_svg"), "Ctrl+E")
        self._act(m, tr("Als &PDF-Bericht exportieren…"), self._on_current("export_pdf"), "Ctrl+P")
        m.addSeparator()
        self._act(m, tr("&Beenden"), self.close, "Ctrl+Q")

        m = mb.addMenu(tr("&Profile"))
        self._act(m, tr("💾 Aktuelles als Profil speichern"), self._on_current("save_profile"), "Ctrl+S")
        self._act(m, tr("📚 Horoskop-Datenbank…"), self.open_database, "Ctrl+D")
        m.addSeparator()
        self._act(m, tr("🧹 Demo-Profile entfernen"), self._clear_demos)
        self._act(m, tr("🔄 Demo-Profile wiederherstellen"), self._restore_demos)

        m = mb.addMenu(tr("&Ansicht"))
        names = [tr("Horoskop"), tr("Analyse"), tr("Prognose"), tr("Synastrie"), tr("Vedisch"), tr("Karte"), tr("KI-Deutung")]
        for i, n in enumerate(names):
            self._act(m, n, lambda i=i: self._goto(i), f"Ctrl+{i + 1}")

        m = mb.addMenu(tr("&KI-Deutung"))
        self._act(m, tr("✨ &KI-Deutung generieren"), self._ai_generate, "Ctrl+G")
        self._act(m, tr("⚙️ KI-&Einstellungen konfigurieren…"), self._on_current("open_ai_settings"))

        m = mb.addMenu(tr("&Einstellungen"))
        self._act(m, tr("&Berechnung & Anzeige…"), self.open_settings, "Ctrl+,")

        m = mb.addMenu(tr("&Hilfe"))
        self._act(m, tr("&Diagnose (Ephemeriden)"), self.show_diagnostics)
        self._act(m, tr("Über &Astrorust"), self.show_about)

    def _create_toolbar(self):
        tb = self.addToolBar(tr("Hauptwerkzeuge"))
        tb.setMovable(False)
        for text, slot, name in [
            (tr("⚡ Berechnen"), self._on_current("calculate"), "btn_start"),
            (tr("🕐 Jetzt"), self._on_current("set_now"), None),
            (tr("➕ Neuer Tab"), self.new_tab, None),
            (tr("📚 Datenbank"), self.open_database, None),
            (tr("🔮 KI-Deutung"), self._goto_ai, None),
            (tr("💾 SVG"), self._on_current("export_svg"), None),
            (tr("📄 PDF"), self._on_current("export_pdf"), None),
            (tr("⚙️ Einstellungen"), self.open_settings, None),
        ]:
            b = QPushButton(text)
            if name:
                b.setObjectName(name)
            b.clicked.connect(lambda checked=False, s=slot: s())
            tb.addWidget(b)
            tb.addSeparator()

    def _goto(self, i):
        v = self.current()
        if v:
            v.tabs.setCurrentIndex(i)

    def _goto_ai(self):
        v = self.current()
        if v:
            v.focus_ai_tab()

    def _ai_generate(self):
        v = self.current()
        if v:
            v.focus_ai_tab()
            v.generate_ai()

    # ─────────────────────── Dialoge ───────────────────────
    def open_settings(self):
        dlg = SettingsDialog(self.backend, self.settings, self)
        old_lang = self.settings.language
        if dlg.exec():
            if self.settings.language != old_lang:
                QMessageBox.information(self, tr("Einstellungen"), tr("Die Sprache wird nach einem Neustart vollständig übernommen."))
            for i in range(self.tabs.count()):
                v = self.tabs.widget(i)
                if isinstance(v, ChartView):
                    if v.person_a.combo_houses:
                        v.person_a.combo_houses.setCurrentText(self.settings.house_system)
                    v.calculate()

    def open_database(self):
        dlg = DatabaseDialog(self.store, self)
        dlg.loadRequested.connect(self._on_db_load)
        dlg.exec()
        for i in range(self.tabs.count()):
            w = self.tabs.widget(i)
            if isinstance(w, ChartView):
                w.refresh_profiles()

    def _on_db_load(self, profile, target):
        if target == "new_tab":
            self.add_tab(profile, calculate=True)
            return
        v = self.current()
        if v:
            v.load_profile(profile, partner=(target == "b"))

    def _clear_demos(self):
        self.store.clear_demos()
        v = self.current()
        if v:
            v.refresh_profiles()

    def _restore_demos(self):
        self.store.restore_demos()
        v = self.current()
        if v:
            v.refresh_profiles()

    def _update_status_hint(self):
        try:
            st = self.backend.call("engine_status")
            files = tr("Datendateien aktiv") if st.get("ephemeris_dir") else tr("Moshier (ohne Datendateien)")
            self.statusBar().showMessage(f"{tr('Astrorust bereit')} — Swiss Ephemeris {st.get('version')} · {files}")
        except Exception:
            self.statusBar().showMessage(tr("Astrorust bereit"))

    def show_diagnostics(self):
        try:
            st = self.backend.call("engine_status")
        except Exception as e:
            QMessageBox.critical(self, tr("Diagnose"), str(e))
            return
        QMessageBox.information(
            self, tr("Diagnose"),
            f"Swiss Ephemeris {st.get('version')}\n\n"
            f"{tr('Ephemeriden-Verzeichnis')}: {st.get('ephemeris_dir') or '—'}\n"
            f"{tr('Chiron/Asteroiden-Datei (seas_18.se1)')}: {'✔' if st.get('asteroids_chiron') else '✘ (' + tr('Näherung aus JPL-Bahnelementen') + ')'}\n"
            f"{tr('Fixsterne (sefstars.txt)')}: {'✔' if st.get('fixed_stars') else '✘'}\n\n"
            f"{tr('Suchpfade')}: $ASTRORUST_EPHE, ~/.local/share/astrorust/ephe, /usr/share/astrorust/ephe")

    def show_about(self):
        QMessageBox.about(
            self, tr("Über Astrorust"),
            "<h3>✨ Astrorust</h3>"
            f"<p><b>{tr('Professionelle Astrologie- und Ephemeriden-Software')}</b></p>"
            f"<p>{tr('Entwickelt in Rust und nativer Qt6-Oberfläche.')}</p>"
            f"<p><b>{tr('Funktionen')}:</b><br>"
            f"• {tr('Swiss Ephemeris 2.10 mit Datendateien (Chiron, Asteroiden, Fixsterne)')}<br>"
            f"• {tr('Historische Zeitzonen und Sommerzeit aus der System-tzdata')}<br>"
            f"• {tr('Progressionen, Solarbogen, Returns, Transitsuche, Himmelskalender')}<br>"
            f"• {tr('Synastrie mit Composite und Davison, Aspektgitter')}<br>"
            f"• {tr('Klassische Würden, Aspektfiguren, Halbsummen, arabische Lose')}<br>"
            f"• {tr('Vedische Astrologie (Nakshatra, Dasha, Vargas)')}<br>"
            f"• {tr('Astrokartografie')}<br>"
            f"• {tr('KI-Deutungen mit Streaming (Claude, Codex, Ollama, API-Keys)')}</p>")
