# -*- coding: utf-8 -*-
"""
Astrorust — Hauptfenster (KDE Breeze Dark / Linux Media Encoder Architektur)
Inklusive nativer KI-Deutungsengine (Claude CLI, Codex CLI, Ollama, GenOffice-Import, API-Keys).
"""

from datetime import datetime, timezone
import os
from PyQt6.QtCore import (
    Qt, QSize, QDate, QTime, QTimer, pyqtSlot
)
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QDateEdit, QTimeEdit,
    QDoubleSpinBox, QGroupBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar, QTextEdit, QFileDialog,
    QMessageBox, QScrollArea, QCompleter, QSlider, QFrame, QApplication
)
from PyQt6.QtGui import QAction, QFont, QColor

import json
import re
from PyQt6.QtWidgets import QCalendarWidget, QDialog
from PyQt6.QtGui import QIcon
from chart_wheel import ChartWheelWidget
from rust_backend import RustBackend
from ai_engine import AiConfig, AiGenerationWorker, detect_environment
from ai_dialog import AiSettingsDialog
import styles

ASTRORUST_CONFIG_DIR = os.path.expanduser("~/.config/astrorust")
ASTRORUST_PROFILES_PATH = os.path.join(ASTRORUST_CONFIG_DIR, "profiles.json")

DEMO_PROFILE_NAMES = {
    "Albert Einstein",
    "Johann Wolfgang von Goethe",
    "Carl Gustav Jung",
    "Marie Curie",
    "Leonardo da Vinci",
    "Aktueller Moment (Jetzt)",
}


class AstroDateEdit(QLineEdit):
    """
    Flexibles, intuitives Datumseingabefeld.
    Erlaubt freies Tippen (z. B. '1985-05-15', '15.05.1985', '1985/05/15'),
    Löschen per Backspace ohne Qt-Sektions-Sperre und bietet zusätzlich
    ein Kalender-Icon zum visuellen Auswählen.
    """
    def __init__(self, default_date=None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("JJJJ-MM-TT oder TT.MM.JJJJ")
        self._current_date = default_date or QDate.currentDate()
        self.setText(self._current_date.toString("yyyy-MM-dd"))

        # Kalender-Icon rechts im Feld
        cal_icon = QIcon.fromTheme("view-calendar", QIcon.fromTheme("x-office-calendar"))
        if cal_icon.isNull():
            cal_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogStart)
        self.cal_action = self.addAction(cal_icon, QLineEdit.ActionPosition.TrailingPosition)
        self.cal_action.setToolTip("Kalender öffnen")
        self.cal_action.triggered.connect(self._open_calendar)

        self.editingFinished.connect(self._on_editing_finished)

    def setDate(self, qdate: QDate):
        if qdate and qdate.isValid():
            self._current_date = qdate
            self.setText(qdate.toString("yyyy-MM-dd"))

    def date(self) -> QDate:
        self._parse_text()
        return self._current_date

    def _parse_text(self):
        text = self.text().strip()
        if not text:
            return

        # 1. Format: JJJJ-MM-TT / JJJJ.MM.TT / JJJJ/MM/TT
        m = re.match(r"^(\d{3,4})[-/.](\d{1,2})[-/.](\d{1,2})$", text)
        if m:
            y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            qd = QDate(y, mth, d)
            if qd.isValid():
                self._current_date = qd
                return

        # 2. Format: TT.MM.JJJJ / TT/MM/JJJJ
        m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{3,4})$", text)
        if m:
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            qd = QDate(y, mth, d)
            if qd.isValid():
                self._current_date = qd
                return

    def _on_editing_finished(self):
        self._parse_text()
        if self._current_date.isValid():
            self.setText(self._current_date.toString("yyyy-MM-dd"))

    def _open_calendar(self):
        self._parse_text()
        dlg = QDialog(self, Qt.WindowType.Popup)
        l = QVBoxLayout(dlg)
        l.setContentsMargins(6, 6, 6, 6)
        cal = QCalendarWidget(dlg)
        cal.setGridVisible(True)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        if self._current_date.isValid():
            cal.setSelectedDate(self._current_date)
        cal.activated.connect(lambda d: (self.setDate(d), dlg.accept()))
        cal.clicked.connect(lambda d: (self.setDate(d), dlg.accept()))
        l.addWidget(cal)

        pos = self.mapToGlobal(self.rect().bottomLeft())
        dlg.move(pos)
        dlg.exec()

    def setCalendarPopup(self, _):
        pass

    def setDisplayFormat(self, _):
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Astrorust — Professionelle Horoskopie & Ephemeriden")
        self.setMinimumSize(QSize(1260, 800))

        self.backend = RustBackend.get()
        self.chart_data = None
        self.transit_data = None
        self.synastry_data = None
        self.mode = "radix"  # "radix", "transit", "synastry"

        self.ai_cfg = AiConfig.load()
        self.ai_worker = None

        # Transit animation timer
        self.transit_datetime = datetime.now(timezone.utc)
        self.transit_timer = QTimer(self)
        self.transit_timer.setInterval(250)
        self.transit_timer.timeout.connect(self._on_transit_tick)

        self._init_ui()
        self._load_profiles()
        self._calculate_current()

    def _init_ui(self):
        # 1. Menüs
        self._create_menus()

        # 2. Toolbar
        self._create_toolbar()

        # 3. Haupt-Layout mit QSplitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setChildrenCollapsible(False)

        left_widget = self._create_left_panel()
        main_splitter.addWidget(left_widget)

        center_widget = self._create_center_panel()
        main_splitter.addWidget(center_widget)

        right_widget = self._create_right_panel()
        main_splitter.addWidget(right_widget)

        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 1)
        main_splitter.setSizes([320, 500, 440])

        self.setCentralWidget(main_splitter)

        # 4. Statusleiste
        self.statusBar().showMessage("Astrorust bereit — Swiss Ephemeris 2.10 Core aktiv")

    # ========================================================
    # Menüleiste & Toolbar
    # ========================================================

    def _create_menus(self):
        menubar = self.menuBar()

        # Datei
        file_menu = menubar.addMenu("&Datei")
        act_calc = file_menu.addAction("&Horoskop berechnen")
        act_calc.setShortcut("F5")
        act_calc.triggered.connect(self._calculate_current)

        act_now = file_menu.addAction("&Jetzt (Live)")
        act_now.setShortcut("F6")
        act_now.triggered.connect(self._set_now)

        file_menu.addSeparator()
        act_export_svg = file_menu.addAction("Als &SVG-Vektorgrafik exportieren...")
        act_export_svg.setShortcut("Ctrl+E")
        act_export_svg.triggered.connect(self._export_svg)

        file_menu.addSeparator()
        act_exit = file_menu.addAction("&Beenden")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)

        # Modus
        mode_menu = menubar.addMenu("&Modus")
        act_m_radix = mode_menu.addAction("☉ &Radix (Geburtshoroskop)")
        act_m_radix.triggered.connect(lambda: self._set_mode("radix"))
        act_m_transit = mode_menu.addAction("⏳ &Transite (Zeitschieber)")
        act_m_transit.triggered.connect(lambda: self._set_mode("transit"))
        act_m_synastry = mode_menu.addAction("👥 &Synastrie (Partner-Vergleich)")
        act_m_synastry.triggered.connect(lambda: self._set_mode("synastry"))

        # Profile
        self.profile_menu = menubar.addMenu("&Profile")

        # KI-Deutung
        ai_menu = menubar.addMenu("&KI-Deutung")
        act_ai_gen = ai_menu.addAction("✨ &KI-Deutung generieren")
        act_ai_gen.setShortcut("Ctrl+G")
        act_ai_gen.triggered.connect(self._generate_ai_interpretation)

        act_ai_settings = ai_menu.addAction("⚙️ &KI-Einstellungen konfigurieren...")
        act_ai_settings.triggered.connect(self._open_ai_settings)

        # Hilfe
        help_menu = menubar.addMenu("&Hilfe")
        act_about = help_menu.addAction("Über &Astrorust")
        act_about.triggered.connect(self._show_about)

    def _create_toolbar(self):
        toolbar = self.addToolBar("Hauptwerkzeuge")
        toolbar.setMovable(False)

        self.btn_calc = QPushButton("⚡ Berechnen")
        self.btn_calc.setObjectName("btn_start")
        self.btn_calc.clicked.connect(self._calculate_current)
        toolbar.addWidget(self.btn_calc)

        toolbar.addSeparator()

        self.btn_now = QPushButton("🕐 Jetzt")
        self.btn_now.clicked.connect(self._set_now)
        toolbar.addWidget(self.btn_now)

        toolbar.addSeparator()

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("☉ Radix", "radix")
        self.combo_mode.addItem("⏳ Transite & Zeitschieber", "transit")
        self.combo_mode.addItem("👥 Synastrie", "synastry")
        self.combo_mode.currentIndexChanged.connect(self._on_mode_combo_changed)
        toolbar.addWidget(self.combo_mode)

        toolbar.addSeparator()

        btn_ai = QPushButton("🔮 KI-Deutung")
        btn_ai.clicked.connect(self._focus_ai_tab)
        toolbar.addWidget(btn_ai)

        toolbar.addSeparator()

        btn_export = QPushButton("💾 SVG Export")
        btn_export.clicked.connect(self._export_svg)
        toolbar.addWidget(btn_export)

    # ========================================================
    # Linkes Panel: Eingabemaske & Zeitschieber
    # ========================================================

    def _create_left_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # 1. Profil-Verwaltung (Speichern & Löschen mit 1 Klick)
        box_profile = QGroupBox("Profile")
        l_prof = QVBoxLayout(box_profile)
        l_prof.setSpacing(6)

        self.combo_profiles = QComboBox()
        self.combo_profiles.currentIndexChanged.connect(self._on_profile_selected)
        l_prof.addWidget(self.combo_profiles)

        h_prof_btns = QHBoxLayout()
        h_prof_btns.setSpacing(6)

        self.btn_save_profile = QPushButton("💾 Speichern")
        self.btn_save_profile.setToolTip("Aktuell eingetragene Daten als Profil speichern")
        self.btn_save_profile.clicked.connect(self._save_current_as_profile)
        h_prof_btns.addWidget(self.btn_save_profile)

        self.btn_delete_profile = QPushButton("🗑️ Löschen")
        self.btn_delete_profile.setToolTip("Ausgewähltes Profil mit 1 Klick löschen")
        self.btn_delete_profile.clicked.connect(self._delete_current_profile)
        h_prof_btns.addWidget(self.btn_delete_profile)

        l_prof.addLayout(h_prof_btns)

        h_demo_actions = QHBoxLayout()
        h_demo_actions.setContentsMargins(0, 2, 0, 0)
        self.btn_clear_demos = QPushButton("🧹 Alle Demos löschen")
        self.btn_clear_demos.setStyleSheet(f"color: {styles.TEXT_MUTED}; font-size: 11px; padding: 2px 4px; border: none; background: transparent; text-align: left;")
        self.btn_clear_demos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_demos.setToolTip("Entfernt alle voreingestellten Demo-Profile (Einstein, Curie, Goethe etc.) auf einmal")
        self.btn_clear_demos.clicked.connect(self._clear_all_demo_profiles)
        h_demo_actions.addWidget(self.btn_clear_demos)

        h_demo_actions.addStretch()

        self.btn_reset_demos = QPushButton("🔄 Demos laden")
        self.btn_reset_demos.setStyleSheet(f"color: {styles.TEXT_MUTED}; font-size: 11px; padding: 2px 4px; border: none; background: transparent; text-align: right;")
        self.btn_reset_demos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_demos.setToolTip("Voreingestellte Demo-Profile wiederherstellen")
        self.btn_reset_demos.clicked.connect(self._restore_demo_profiles)
        h_demo_actions.addWidget(self.btn_reset_demos)

        l_prof.addLayout(h_demo_actions)
        layout.addWidget(box_profile)

        # 2. Person A (Radix) Eingabe
        self.box_natal = QGroupBox("Geburtsdaten (Radix)")
        l_nat = QGridLayout(self.box_natal)
        l_nat.setSpacing(6)

        l_nat.addWidget(QLabel("Name:"), 0, 0)
        self.edit_name = QLineEdit("Albert Einstein")
        l_nat.addWidget(self.edit_name, 0, 1, 1, 2)

        l_nat.addWidget(QLabel("Datum:"), 1, 0)
        self.edit_date = AstroDateEdit(QDate(1879, 3, 14))
        l_nat.addWidget(self.edit_date, 1, 1)

        self.edit_time = QTimeEdit()
        self.edit_time.setDisplayFormat("HH:mm")
        self.edit_time.setTime(QTime(11, 30))
        l_nat.addWidget(self.edit_time, 1, 2)

        l_nat.addWidget(QLabel("Geburtsort:"), 2, 0)
        self.edit_city = QLineEdit("Ulm, Deutschland")
        self._setup_city_completer(self.edit_city)
        l_nat.addWidget(self.edit_city, 2, 1, 1, 2)

        l_nat.addWidget(QLabel("Breite (°):"), 3, 0)
        self.spin_lat = QDoubleSpinBox()
        self.spin_lat.setRange(-90.0, 90.0)
        self.spin_lat.setDecimals(4)
        self.spin_lat.setValue(48.4011)
        l_nat.addWidget(self.spin_lat, 3, 1)

        l_nat.addWidget(QLabel("Länge (°):"), 3, 2)
        self.spin_lon = QDoubleSpinBox()
        self.spin_lon.setRange(-180.0, 180.0)
        self.spin_lon.setDecimals(4)
        self.spin_lon.setValue(9.9876)
        l_nat.addWidget(self.spin_lon, 3, 3)

        l_nat.addWidget(QLabel("Zone (h):"), 4, 0)
        self.spin_tz = QDoubleSpinBox()
        self.spin_tz.setRange(-12.0, 14.0)
        self.spin_tz.setDecimals(2)
        self.spin_tz.setValue(1.0)
        l_nat.addWidget(self.spin_tz, 4, 1)

        l_nat.addWidget(QLabel("Häusersystem:"), 5, 0)
        self.combo_houses = QComboBox()
        self.combo_houses.addItems([
            "Placidus", "Koch", "Regiomontanus", "Campanus",
            "WholeSign", "Equal", "Topocentric", "Porphyry"
        ])
        l_nat.addWidget(self.combo_houses, 5, 1, 1, 2)

        layout.addWidget(self.box_natal)

        # 3. Person B (Synastrie) Eingabe
        self.box_synastry = QGroupBox("Partner / Person B")
        self.box_synastry.setVisible(False)
        l_syn = QGridLayout(self.box_synastry)
        l_syn.setSpacing(6)

        l_syn.addWidget(QLabel("Name B:"), 0, 0)
        self.edit_name_b = QLineEdit("Mileva Marić")
        l_syn.addWidget(self.edit_name_b, 0, 1, 1, 2)

        l_syn.addWidget(QLabel("Datum:"), 1, 0)
        self.edit_date_b = AstroDateEdit(QDate(1875, 12, 19))
        l_syn.addWidget(self.edit_date_b, 1, 1)

        self.edit_time_b = QTimeEdit()
        self.edit_time_b.setDisplayFormat("HH:mm")
        self.edit_time_b.setTime(QTime(12, 0))
        l_syn.addWidget(self.edit_time_b, 1, 2)

        l_syn.addWidget(QLabel("Ort:"), 2, 0)
        self.edit_city_b = QLineEdit("Titel, Serbien")
        self._setup_city_completer(self.edit_city_b)
        l_syn.addWidget(self.edit_city_b, 2, 1, 1, 2)

        l_syn.addWidget(QLabel("Breite:"), 3, 0)
        self.spin_lat_b = QDoubleSpinBox()
        self.spin_lat_b.setRange(-90.0, 90.0)
        self.spin_lat_b.setValue(45.2056)
        l_syn.addWidget(self.spin_lat_b, 3, 1)

        l_syn.addWidget(QLabel("Länge:"), 3, 2)
        self.spin_lon_b = QDoubleSpinBox()
        self.spin_lon_b.setRange(-180.0, 180.0)
        self.spin_lon_b.setValue(20.0944)
        l_syn.addWidget(self.spin_lon_b, 3, 3)

        l_syn.addWidget(QLabel("Zone:"), 4, 0)
        self.spin_tz_b = QDoubleSpinBox()
        self.spin_tz_b.setValue(1.0)
        l_syn.addWidget(self.spin_tz_b, 4, 1)

        layout.addWidget(self.box_synastry)

        # 4. Der Zeitschieber
        self.box_transit = QGroupBox("⏳ Zeitschieber (Transite)")
        self.box_transit.setVisible(False)
        l_tr = QVBoxLayout(self.box_transit)
        l_tr.setSpacing(8)

        self.lbl_transit_clock = QLabel("2026-10-12 07:30 UTC")
        self.lbl_transit_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_transit_clock.setStyleSheet(
            f"font-family: monospace; font-size: 13px; font-weight: bold; color: {styles.ACCENT}; background: {styles.SURFACE_SUNKEN}; padding: 6px; border-radius: 4px;"
        )
        l_tr.addWidget(self.lbl_transit_clock)

        # Step Buttons
        h_steps1 = QHBoxLayout()
        h_steps1.setSpacing(3)
        for label, delta in [("-1J", -31536000), ("-1M", -2592000), ("-1T", -86400), ("-1h", -3600), ("-10m", -600)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, d=delta: self._step_transit(d))
            h_steps1.addWidget(btn)
        l_tr.addLayout(h_steps1)

        h_play = QHBoxLayout()
        self.btn_play_transit = QPushButton("▶ Animation starten")
        self.btn_play_transit.setObjectName("btn_play")
        self.btn_play_transit.clicked.connect(self._toggle_transit_play)
        h_play.addWidget(self.btn_play_transit)

        btn_tr_now = QPushButton("Jetzt")
        btn_tr_now.clicked.connect(self._reset_transit_now)
        h_play.addWidget(btn_tr_now)
        l_tr.addLayout(h_play)

        h_steps2 = QHBoxLayout()
        h_steps2.setSpacing(3)
        for label, delta in [("+10m", 600), ("+1h", 3600), ("+1T", 86400), ("+1M", 2592000), ("+1J", 31536000)]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, d=delta: self._step_transit(d))
            h_steps2.addWidget(btn)
        l_tr.addLayout(h_steps2)

        l_tr.addWidget(QLabel("Zeitschieber-Regler:"))
        self.slider_transit = QSlider(Qt.Orientation.Horizontal)
        self.slider_transit.setRange(-30, 30)
        self.slider_transit.setValue(0)
        self.slider_transit.valueChanged.connect(self._on_slider_scrub)
        l_tr.addWidget(self.slider_transit)

        layout.addWidget(self.box_transit)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _setup_city_completer(self, line_edit):
        cities = self.backend.search_cities("")
        names = [f"{c['name']}, {c['country']}" for c in cities]
        completer = QCompleter(names, line_edit)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        line_edit.setCompleter(completer)

        def on_activated(text):
            for c in cities:
                if f"{c['name']}, {c['country']}" == text:
                    self.spin_lat.setValue(c["latitude"])
                    self.spin_lon.setValue(c["longitude"])
                    self.spin_tz.setValue(c["default_tz"])
                    break
        completer.activated.connect(on_activated)

    # ========================================================
    # Mittleres Panel: Natives Horoskop-Rad (QPainter)
    # ========================================================

    def _create_center_panel(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)

        header_box = QFrame()
        header_box.setStyleSheet(
            f"background: {styles.SURFACE_RAISED}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 6px; padding: 6px;"
        )
        h_layout = QHBoxLayout(header_box)
        h_layout.setContentsMargins(6, 4, 6, 4)

        v_head = QVBoxLayout()
        self.lbl_chart_name = QLabel("Albert Einstein")
        self.lbl_chart_name.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {styles.TEXT};")
        v_head.addWidget(self.lbl_chart_name)

        self.lbl_chart_meta = QLabel("1879-03-14 11:30 • Ulm, Deutschland • Placidus")
        self.lbl_chart_meta.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
        v_head.addWidget(self.lbl_chart_meta)
        h_layout.addLayout(v_head)
        h_layout.addStretch()

        leg_layout = QHBoxLayout()
        leg_layout.setSpacing(10)
        for name, color in [("Feuer", styles.COLOR_FIRE), ("Erde", styles.COLOR_EARTH), ("Luft", styles.COLOR_AIR), ("Wasser", styles.COLOR_WATER)]:
            dot = QLabel(f"<span style='color:{color}; font-size:14px;'>●</span> {name}")
            dot.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
            leg_layout.addWidget(dot)
        h_layout.addLayout(leg_layout)

        layout.addWidget(header_box)

        self.chart_wheel = ChartWheelWidget()
        self.chart_wheel.planet_selected.connect(self._on_wheel_planet_selected)
        layout.addWidget(self.chart_wheel, 1)

        angles_bar = QFrame()
        angles_bar.setStyleSheet(f"background: {styles.SURFACE_SUNKEN}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 4px;")
        ab_layout = QHBoxLayout(angles_bar)
        ab_layout.setContentsMargins(6, 4, 6, 4)

        self.lbl_asc = QLabel("AC: —")
        self.lbl_mc = QLabel("MC: —")
        self.lbl_desc = QLabel("DC: —")
        self.lbl_ic = QLabel("IC: —")
        self.lbl_fortune = QLabel("⊗: —")

        for lbl in (self.lbl_asc, self.lbl_mc, self.lbl_desc, self.lbl_ic, self.lbl_fortune):
            lbl.setStyleSheet(f"font-family: monospace; font-size: 11px; color: {styles.ACCENT}; font-weight: bold;")
            ab_layout.addWidget(lbl)
            ab_layout.addStretch()

        layout.addWidget(angles_bar)
        return container

    # ========================================================
    # Rechtes Panel: Tabbed Data & KI-Deutung Dashboard
    # ========================================================

    def _create_right_panel(self):
        self.tabs = QTabWidget()

        # Tab 1: Planeten-Tabelle
        self.table_planets = QTableWidget()
        self.table_planets.setColumnCount(6)
        self.table_planets.setHorizontalHeaderLabels(["Pt", "Planet", "Position", "H", "Würde", "Rx"])
        self.table_planets.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_planets.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.table_planets, "Planeten")

        # Tab 2: Aspektarium
        tab_aspects = QWidget()
        v_asp = QVBoxLayout(tab_aspects)
        v_asp.setContentsMargins(4, 4, 4, 4)
        self.table_aspects = QTableWidget()
        self.table_aspects.cellClicked.connect(self._on_aspect_cell_clicked)
        v_asp.addWidget(self.table_aspects, 1)

        self.lbl_aspect_detail = QLabel("Klicken Sie auf ein Feld im Aspektarium für Details.")
        self.lbl_aspect_detail.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED}; background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px;")
        v_asp.addWidget(self.lbl_aspect_detail)
        self.tabs.addTab(tab_aspects, "Aspektarium")

        # Tab 3: Häuserspitzen
        self.table_houses = QTableWidget()
        self.table_houses.setColumnCount(4)
        self.table_houses.setHorizontalHeaderLabels(["Haus", "Cusp", "Zeichen", "Position"])
        self.table_houses.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.table_houses, "Häuser")

        # Tab 4: Elemente & Qualitäten
        self.tab_elements = QWidget()
        self.l_elem = QVBoxLayout(self.tab_elements)
        self.l_elem.setContentsMargins(12, 12, 12, 12)
        self.tabs.addTab(self.tab_elements, "Elemente")

        # Tab 5: Regel-Deutung (deterministisch)
        self.text_deutung = QTextEdit()
        self.text_deutung.setReadOnly(True)
        self.tabs.addTab(self.text_deutung, "Regel-Deutung")

        # Tab 6: Transite
        self.table_transits = QTableWidget()
        self.table_transits.setColumnCount(4)
        self.table_transits.setHorizontalHeaderLabels(["Transit", "Aspekt", "Radix", "Orbis"])
        self.table_transits.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.table_transits, "Transite")

        # Tab 7: 🔮 KI-Deutung (Umfassend & tiefenpsychologisch)
        tab_ai = self._create_ai_tab()
        self.tabs.addTab(tab_ai, "🔮 KI-Deutung")

        return self.tabs

    def _create_ai_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Steuerungsleiste
        top_bar = QFrame()
        top_bar.setStyleSheet(f"background: {styles.SURFACE_SUNKEN}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 5px; padding: 6px;")
        v_tb = QVBoxLayout(top_bar)
        v_tb.setContentsMargins(4, 4, 4, 4)
        v_tb.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Thema:"))
        self.combo_ai_module = QComboBox()
        self.combo_ai_module.addItem("🌟 Großes Radix-Persönlichkeitsprofil", "gesamt")
        self.combo_ai_module.addItem("🏛️ Berufung, Karriere & Lebensziel (MC & Haus 10)", "beruf")
        self.combo_ai_module.addItem("💖 Partnerschaft, Liebe & Beziehung (Venus, Mars & Haus 7)", "partnerschaft")
        self.combo_ai_module.addItem("🌙 Seelenleben & emotionale Wurzeln (Mond & Haus 4)", "seelenleben")
        self.combo_ai_module.addItem("🪐 Karma, Seelenplan & Schattenarbeit (Saturn, Chiron, Knoten)", "karma")
        self.combo_ai_module.addItem("⏳ Aktuelle Transite & Zeitqualität (Jahresvorschau)", "transite")
        self.combo_ai_module.addItem("👥 Partnervergleich & Beziehungsdynamik (Synastrie)", "synastrie")
        row1.addWidget(self.combo_ai_module, 1)

        btn_settings = QPushButton("⚙️ Einstellungen")
        btn_settings.setToolTip("KI-Provider, API-Keys oder lokale Modelle konfigurieren")
        btn_settings.clicked.connect(self._open_ai_settings)
        row1.addWidget(btn_settings)

        v_tb.addLayout(row1)

        row2 = QHBoxLayout()
        self.btn_ai_generate = QPushButton("✨ KI-Deutung generieren")
        self.btn_ai_generate.setObjectName("btn_start")
        self.btn_ai_generate.clicked.connect(self._generate_ai_interpretation)
        row2.addWidget(self.btn_ai_generate, 1)

        self.btn_ai_cancel = QPushButton("⏹ Abbrechen")
        self.btn_ai_cancel.setEnabled(False)
        self.btn_ai_cancel.clicked.connect(self._cancel_ai_generation)
        row2.addWidget(self.btn_ai_cancel)

        v_tb.addLayout(row2)
        layout.addWidget(top_bar)

        # Status / Ladebalken
        self.lbl_ai_status = QLabel("Bereit zur KI-Generierung.")
        self.lbl_ai_status.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
        layout.addWidget(self.lbl_ai_status)

        self.progress_ai = QProgressBar()
        self.progress_ai.setRange(0, 0)  # Infinite pulse
        self.progress_ai.setVisible(False)
        layout.addWidget(self.progress_ai)

        # Textausgabe
        self.text_ai_output = QTextEdit()
        self.text_ai_output.setReadOnly(True)
        self.text_ai_output.setPlaceholderText("Die generierte astrologische Deutung erscheint hier in vollständigem Markdown...")
        layout.addWidget(self.text_ai_output, 1)

        # Aktionen unten
        h_act = QHBoxLayout()
        btn_copy = QPushButton("📋 Kopieren")
        btn_copy.clicked.connect(self._copy_ai_text)
        h_act.addWidget(btn_copy)

        btn_save = QPushButton("💾 Als Text speichern")
        btn_save.clicked.connect(self._save_ai_text)
        h_act.addWidget(btn_save)

        h_act.addStretch()
        layout.addLayout(h_act)

        return container

    # ========================================================
    # KI-Aktionen & Steuerung
    # ========================================================

    def _focus_ai_tab(self):
        # Index of KI-Deutung tab is 6
        self.tabs.setCurrentIndex(6)

    def _open_ai_settings(self):
        dlg = AiSettingsDialog(self)
        if dlg.exec():
            self.ai_cfg = AiConfig.load()
            prov = self.ai_cfg.get("active_provider", "auto")
            self.lbl_ai_status.setText(f"Aktiver KI-Provider aktualisiert: {prov}")

    def _generate_ai_interpretation(self):
        if not self.chart_data:
            QMessageBox.warning(self, "Hinweis", "Bitte zuerst ein Horoskop berechnen.")
            return

        self._focus_ai_tab()
        self.ai_cfg = AiConfig.load()
        module_key = self.combo_ai_module.currentData()

        # If transit module, ensure transit chart exists
        tr_chart = self.transit_data if (module_key == "transite" or self.mode == "transit") else None
        syn_chart = self.transit_data if (module_key == "synastrie" or self.mode == "synastry") else None

        self.btn_ai_generate.setEnabled(False)
        self.btn_ai_cancel.setEnabled(True)
        self.progress_ai.setVisible(True)
        self.lbl_ai_status.setText("KI-Modell wird initialisiert...")

        self.ai_worker = AiGenerationWorker(
            self.chart_data, module_key, self.ai_cfg, tr_chart, syn_chart
        )
        self.ai_worker.status_signal.connect(self._on_ai_status)
        self.ai_worker.finished_signal.connect(self._on_ai_finished)
        self.ai_worker.error_signal.connect(self._on_ai_error)
        self.ai_worker.start()

    def _cancel_ai_generation(self):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.cancel()
            self.ai_worker.terminate()
            self._reset_ai_ui("Generierung abgebrochen.")

    def _on_ai_status(self, msg):
        self.lbl_ai_status.setText(msg)

    def _on_ai_finished(self, text):
        self.text_ai_output.setMarkdown(text)
        self._reset_ai_ui("Deutung erfolgreich generiert!")

    def _on_ai_error(self, err):
        self._reset_ai_ui(f"Fehler: {err}")
        QMessageBox.critical(self, "KI-Fehler", f"Fehler bei der KI-Generierung:\n\n{err}\n\nPrüfen Sie Ihre Einstellungen unter '⚙️ Einstellungen'.")

    def _reset_ai_ui(self, status_msg):
        self.btn_ai_generate.setEnabled(True)
        self.btn_ai_cancel.setEnabled(False)
        self.progress_ai.setVisible(False)
        self.lbl_ai_status.setText(status_msg)

    def _copy_ai_text(self):
        txt = self.text_ai_output.toPlainText()
        if txt:
            QApplication.clipboard().setText(txt)
            self.statusBar().showMessage("KI-Deutung in die Zwischenablage kopiert!", 3000)

    def _save_ai_text(self):
        txt = self.text_ai_output.toPlainText()
        if not txt:
            return
        name = self.chart_data.get("name", "Horoskop")
        fn, _ = QFileDialog.getSaveFileName(
            self, "Deutung als Text speichern", f"{name}_Deutung.md", "Markdown (*.md);;Textdatei (*.txt)"
        )
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(txt)
            self.statusBar().showMessage(f"Gespeichert unter {fn}", 4000)

    # ========================================================
    # Datenverarbeitung & Horoskop-Berechnungen
    # ========================================================

    def _init_profiles(self):
        self.saved_profiles = []
        if os.path.exists(ASTRORUST_PROFILES_PATH):
            try:
                with open(ASTRORUST_PROFILES_PATH, "r", encoding="utf-8") as f:
                    self.saved_profiles = json.load(f)
            except Exception as e:
                print("Fehler beim Laden von profiles.json:", e)
                self.saved_profiles = []
        else:
            # Erster Start: Demo-Profile aus Backend als Initialbestand laden & persistieren
            try:
                self.saved_profiles = self.backend.get_profiles()
                self._save_profiles_to_disk()
            except Exception:
                self.saved_profiles = []

    def _save_profiles_to_disk(self):
        try:
            os.makedirs(ASTRORUST_CONFIG_DIR, exist_ok=True)
            with open(ASTRORUST_PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(self.saved_profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Fehler beim Speichern von profiles.json:", e)

    def _refresh_profiles_ui(self, select_name=None):
        self.combo_profiles.blockSignals(True)
        self.combo_profiles.clear()

        if not self.saved_profiles:
            self.combo_profiles.addItem("(Keine Profile gespeichert)", None)
            self.btn_delete_profile.setEnabled(False)
        else:
            self.btn_delete_profile.setEnabled(True)
            target_idx = 0
            for idx, p in enumerate(self.saved_profiles):
                self.combo_profiles.addItem(p["name"], p)
                if select_name and p.get("name") == select_name:
                    target_idx = idx

            self.combo_profiles.setCurrentIndex(target_idx)

        self.combo_profiles.blockSignals(False)
        self._refresh_profile_menu()

    def _refresh_profile_menu(self):
        self.profile_menu.clear()

        act_save = self.profile_menu.addAction("💾 Aktuelles als Profil speichern")
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_current_as_profile)

        act_del = self.profile_menu.addAction("🗑️ Ausgewähltes Profil löschen")
        act_del.triggered.connect(self._delete_current_profile)

        self.profile_menu.addSeparator()

        act_clear_demo = self.profile_menu.addAction("🧹 Demo-Profile entfernen")
        act_clear_demo.triggered.connect(self._clear_all_demo_profiles)

        act_reset_demo = self.profile_menu.addAction("🔄 Demo-Profile wiederherstellen")
        act_reset_demo.triggered.connect(self._restore_demo_profiles)

        self.profile_menu.addSeparator()

        for p in self.saved_profiles:
            act = self.profile_menu.addAction(p["name"])
            act.triggered.connect(lambda _, prof=p: self._apply_profile(prof))

    def _save_current_as_profile(self):
        d = self.edit_date.date()
        t = self.edit_time.time()
        name = self.edit_name.text().strip()
        if not name:
            name = "Mein Profil"
            self.edit_name.setText(name)

        new_prof = {
            "name": name,
            "year": d.year(),
            "month": d.month(),
            "day": d.day(),
            "hour": t.hour(),
            "minute": t.minute(),
            "second": 0,
            "timezone_offset": self.spin_tz.value(),
            "latitude": self.spin_lat.value(),
            "longitude": self.spin_lon.value(),
            "location_name": self.edit_city.text().strip(),
            "house_system": self.combo_houses.currentText(),
        }

        # Falls Profil mit selbem Namen existiert -> aktualisieren, sonst anhängen
        updated = False
        for idx, p in enumerate(self.saved_profiles):
            if p.get("name") == name:
                self.saved_profiles[idx] = new_prof
                updated = True
                break
        if not updated:
            self.saved_profiles.append(new_prof)

        self._save_profiles_to_disk()
        self._refresh_profiles_ui(select_name=name)
        self.statusBar().showMessage(f"Profil '{name}' erfolgreich gespeichert!", 4000)

    def _delete_current_profile(self):
        idx = self.combo_profiles.currentIndex()
        if idx < 0 or not self.saved_profiles:
            return

        p = self.combo_profiles.itemData(idx)
        if not p:
            return

        del_name = p.get("name", "Profil")
        self.saved_profiles = [x for x in self.saved_profiles if x.get("name") != del_name]
        self._save_profiles_to_disk()
        self._refresh_profiles_ui()

        if self.saved_profiles:
            self._apply_profile(self.saved_profiles[0])
        self.statusBar().showMessage(f"Profil '{del_name}' gelöscht.", 4000)

    def _clear_all_demo_profiles(self):
        self.saved_profiles = [
            p for p in self.saved_profiles if p.get("name") not in DEMO_PROFILE_NAMES
        ]
        self._save_profiles_to_disk()
        self._refresh_profiles_ui()

        if self.saved_profiles:
            self._apply_profile(self.saved_profiles[0])
        self.statusBar().showMessage("Alle Demo-Profile wurden entfernt.", 4000)

    def _restore_demo_profiles(self):
        demos = self.backend.get_profiles()
        existing_names = {p.get("name") for p in self.saved_profiles}
        for d in demos:
            if d.get("name") not in existing_names:
                self.saved_profiles.append(d)
        self._save_profiles_to_disk()
        self._refresh_profiles_ui()
        self.statusBar().showMessage("Demo-Profile wiederhergestellt.", 4000)

    def _load_profiles(self):
        self._init_profiles()
        self._refresh_profiles_ui()
        if self.saved_profiles:
            self._apply_profile(self.saved_profiles[0])

    def _apply_profile(self, p):
        self.edit_name.setText(p.get("name", ""))
        self.edit_date.setDate(QDate(p.get("year", 2000), p.get("month", 1), p.get("day", 1)))
        self.edit_time.setTime(QTime(p.get("hour", 12), p.get("minute", 0)))
        self.edit_city.setText(p.get("location_name", ""))
        self.spin_lat.setValue(p.get("latitude", 52.52))
        self.spin_lon.setValue(p.get("longitude", 13.405))
        self.spin_tz.setValue(p.get("timezone_offset", 1.0))

        hs = p.get("house_system", "Placidus")
        idx = self.combo_houses.findText(hs)
        if idx >= 0:
            self.combo_houses.setCurrentIndex(idx)

        self._calculate_current()

    def _on_profile_selected(self, index):
        if index < 0 or not self.saved_profiles:
            return
        p = self.combo_profiles.itemData(index)
        if p:
            self._apply_profile(p)

    def _get_request_dict(self):
        d = self.edit_date.date()
        t = self.edit_time.time()
        return {
            "name": self.edit_name.text(),
            "year": d.year(),
            "month": d.month(),
            "day": d.day(),
            "hour": t.hour(),
            "minute": t.minute(),
            "second": 0,
            "timezone_offset": self.spin_tz.value(),
            "latitude": self.spin_lat.value(),
            "longitude": self.spin_lon.value(),
            "location_name": self.edit_city.text(),
            "house_system": self.combo_houses.currentText(),
        }

    def _calculate_current(self):
        req = self._get_request_dict()
        try:
            self.chart_data = self.backend.calculate_chart(req)
            self._render_chart_data()

            if self.mode == "transit":
                self._update_transits()
            elif self.mode == "synastry":
                self._update_synastry()
            else:
                self.chart_wheel.set_data(self.chart_data, None, "radix")

            self.statusBar().showMessage(
                f"Horoskop für {self.chart_data['name']} erfolgreich berechnet (JD: {self.chart_data['julian_day']:.4f})"
            )
        except Exception as e:
            QMessageBox.critical(self, "Berechnungsfehler", str(e))

    def _render_chart_data(self):
        c = self.chart_data

        self.lbl_chart_name.setText(c["name"])
        self.lbl_chart_meta.setText(
            f"{c['date_time']} • {c['location_name']} • Häuser: {c['house_system']}"
        )

        ang = c["angles"]
        self.lbl_asc.setText(f"AC: {ang['ascendant_formatted']}")
        self.lbl_mc.setText(f"MC: {ang['midheaven_formatted']}")
        self.lbl_desc.setText(f"DC: {ang['descendant_formatted']}")
        self.lbl_ic.setText(f"IC: {ang['imum_coeli_formatted']}")
        self.lbl_fortune.setText(f"⊗: {ang['part_of_fortune_formatted']}")

        # 1. Planeten Tabelle
        planets = c.get("planets", [])
        self.table_planets.setRowCount(len(planets))
        for row, p in enumerate(planets):
            self.table_planets.setItem(row, 0, QTableWidgetItem(p["glyph"]))
            self.table_planets.setItem(row, 1, QTableWidgetItem(p["name"]))
            pos_str = f"{p['formatted_deg']} {p['sign_glyph']}"
            self.table_planets.setItem(row, 2, QTableWidgetItem(pos_str))
            self.table_planets.setItem(row, 3, QTableWidgetItem(f"{p['house']}."))

            dig = p.get("dignity") or "—"
            dig_item = QTableWidgetItem(dig)
            if dig == "Domizil":
                dig_item.setForeground(QColor(styles.COLOR_EARTH))
            elif dig == "Erhöhung":
                dig_item.setForeground(QColor(styles.COLOR_AIR))
            elif dig in ("Fall", "Exil"):
                dig_item.setForeground(QColor(styles.STOP_RED))
            self.table_planets.setItem(row, 4, dig_item)

            rx_str = "℞" if p["is_retrograde"] else "•"
            rx_item = QTableWidgetItem(rx_str)
            if p["is_retrograde"]:
                rx_item.setForeground(QColor(styles.STOP_RED))
            self.table_planets.setItem(row, 5, rx_item)

        # 2. Aspektarium Tabelle (Dreieck)
        self._render_aspectarium(planets, c.get("aspects", []))

        # 3. Häuser Tabelle
        houses = c.get("houses", [])
        self.table_houses.setRowCount(len(houses))
        for row, h in enumerate(houses):
            h_num = h["house_number"]
            cusp_name = "AC" if h_num == 1 else ("MC" if h_num == 10 else ("DC" if h_num == 7 else ("IC" if h_num == 4 else "")))
            self.table_houses.setItem(row, 0, QTableWidgetItem(f"Haus {h_num}"))
            self.table_houses.setItem(row, 1, QTableWidgetItem(cusp_name))
            self.table_houses.setItem(row, 2, QTableWidgetItem(f"{h['sign_glyph']} {h['sign_name']}"))
            self.table_houses.setItem(row, 3, QTableWidgetItem(h["formatted_deg"]))

        # 4. Elemente & Qualitäten
        self._render_elements(c.get("element_quality", {}))

        # 5. Regel-Deutung
        self._render_interpretations(c.get("interpretations", []))

    def _render_aspectarium(self, planets, aspects):
        n = len(planets)
        self.table_aspects.setRowCount(n)
        self.table_aspects.setColumnCount(n)

        headers = [p["glyph"] for p in planets]
        self.table_aspects.setHorizontalHeaderLabels(headers)
        self.table_aspects.setVerticalHeaderLabels(headers)

        for r in range(n):
            for col in range(n):
                if col < r:
                    p1 = planets[r]
                    p2 = planets[col]
                    asp = next(
                        (a for a in aspects if (a["point_a"] == p1["id"] and a["point_b"] == p2["id"]) or (a["point_a"] == p2["id"] and a["point_b"] == p1["id"])),
                        None
                    )
                    if asp:
                        item = QTableWidgetItem(asp["aspect_glyph"])
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        item.setForeground(QColor(asp.get("color_hex", styles.ACCENT)))
                        item.setData(Qt.ItemDataRole.UserRole, asp)
                        self.table_aspects.setItem(r, col, item)
                    else:
                        self.table_aspects.setItem(r, col, QTableWidgetItem(""))
                else:
                    item = QTableWidgetItem("")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                    self.table_aspects.setItem(r, col, item)

        self.table_aspects.resizeColumnsToContents()
        self.table_aspects.resizeRowsToContents()

    def _on_aspect_cell_clicked(self, row, col):
        item = self.table_aspects.item(row, col)
        if not item:
            return
        asp = item.data(Qt.ItemDataRole.UserRole)
        if asp:
            txt = (
                f"<b>{asp['point_a_name']} {asp['aspect_glyph']} {asp['aspect_name']} {asp['point_b_name']}</b><br>"
                f"Exakter Winkel: {asp['actual_angle']:.2f}° (Soll: {asp['target_angle']:.1f}°) • Orbis: {asp['formatted_orb']}<br>"
                f"Status: {'Applikativ (zunehmend)' if asp.get('is_applying') else 'Separativ (abnehmend)'}"
            )
            self.lbl_aspect_detail.setText(txt)

    def _render_elements(self, eq):
        while self.l_elem.count():
            item = self.l_elem.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tot_elem = max(1, eq.get("fire", 0) + eq.get("earth", 0) + eq.get("air", 0) + eq.get("water", 0))
        tot_qual = max(1, eq.get("cardinal", 0) + eq.get("fixed", 0) + eq.get("mutable", 0))

        box_e = QGroupBox(f"Vier Elemente (Dominant: {eq.get('dominant_element', '—')})")
        l_e = QVBoxLayout(box_e)
        for name, val, col in [("Feuer", eq.get("fire", 0), styles.COLOR_FIRE), ("Erde", eq.get("earth", 0), styles.COLOR_EARTH), ("Luft", eq.get("air", 0), styles.COLOR_AIR), ("Wasser", eq.get("water", 0), styles.COLOR_WATER)]:
            h = QHBoxLayout()
            h.addWidget(QLabel(f"{name}:"))
            p = QProgressBar()
            p.setRange(0, tot_elem)
            p.setValue(val)
            p.setStyleSheet(f"QProgressBar::chunk {{ background-color: {col}; }}")
            h.addWidget(p)
            h.addWidget(QLabel(str(val)))
            l_e.addLayout(h)
        self.l_elem.addWidget(box_e)

        box_q = QGroupBox(f"Drei Qualitäten (Dominant: {eq.get('dominant_quality', '—')})")
        l_q = QVBoxLayout(box_q)
        for name, val, col in [("Kardinal", eq.get("cardinal", 0), styles.ACCENT), ("Fix", eq.get("fixed", 0), styles.COLOR_AIR), ("Veränderlich", eq.get("mutable", 0), "#a855f7")]:
            h = QHBoxLayout()
            h.addWidget(QLabel(f"{name}:"))
            p = QProgressBar()
            p.setRange(0, tot_qual)
            p.setValue(val)
            p.setStyleSheet(f"QProgressBar::chunk {{ background-color: {col}; }}")
            h.addWidget(p)
            h.addWidget(QLabel(str(val)))
            l_q.addLayout(h)
        self.l_elem.addWidget(box_q)
        self.l_elem.addStretch()

    def _render_interpretations(self, interps):
        html = ""
        for sec in interps:
            html += f"<h3 style='color:{styles.ACCENT}; margin-bottom:2px;'>{sec.get('title')}</h3>"
            html += f"<div style='color:{styles.TEXT_MUTED}; font-size:10px; text-transform:uppercase;'>{sec.get('subtitle')}</div>"
            html += f"<p style='margin-top:4px; line-height:1.4;'>{sec.get('text')}</p>"
            tags = " • ".join(sec.get("keywords", []))
            html += f"<div style='color:{styles.COLOR_AIR}; font-size:10px; margin-bottom:12px;'>Schlagwörter: {tags}</div><hr style='border:none; border-bottom:1px solid {styles.BORDER_SOFT};'>"
        self.text_deutung.setHtml(html)

    def _on_wheel_planet_selected(self, planet):
        for row in range(self.table_planets.rowCount()):
            item = self.table_planets.item(row, 1)
            if item and item.text() == planet.get("name"):
                self.table_planets.selectRow(row)
                self.tabs.setCurrentIndex(0)
                break

    # ========================================================
    # Transite & Zeitschieber
    # ========================================================

    def _step_transit(self, delta_seconds):
        self.transit_datetime = datetime.fromtimestamp(
            self.transit_datetime.timestamp() + delta_seconds, timezone.utc
        )
        self._update_transits()

    def _toggle_transit_play(self):
        if self.transit_timer.isActive():
            self.transit_timer.stop()
            self.btn_play_transit.setText("▶ Animation starten")
            self.btn_play_transit.setProperty("class", "")
        else:
            self.transit_timer.start()
            self.btn_play_transit.setText("⏸ Pause")
            self.btn_play_transit.setProperty("class", "playing")
        self.btn_play_transit.style().unpolish(self.btn_play_transit)
        self.btn_play_transit.style().polish(self.btn_play_transit)

    def _on_transit_tick(self):
        self._step_transit(86400)

    def _reset_transit_now(self):
        self.transit_datetime = datetime.now(timezone.utc)
        self._update_transits()

    def _on_slider_scrub(self, val):
        now = datetime.now(timezone.utc)
        offset_seconds = val * 365.25 * 86400
        self.transit_datetime = datetime.fromtimestamp(now.timestamp() + offset_seconds, timezone.utc)
        self._update_transits()

    def _update_transits(self):
        if not self.chart_data:
            return

        dt = self.transit_datetime
        clock_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        self.lbl_transit_clock.setText(clock_str)

        req = {
            "natal": self._get_request_dict(),
            "transit_year": dt.year,
            "transit_month": dt.month,
            "transit_day": dt.day,
            "transit_hour": dt.hour,
            "transit_minute": dt.minute,
            "transit_timezone_offset": 0.0,
        }

        try:
            res = self.backend.calculate_transit(req)
            self.transit_data = res["transit_chart"]
            self.chart_wheel.set_data(self.chart_data, self.transit_data, "transit")

            tr_aspects = res.get("transit_aspects", [])
            self.table_transits.setRowCount(len(tr_aspects))
            for row, asp in enumerate(tr_aspects):
                self.table_transits.setItem(row, 0, QTableWidgetItem(f"{asp['transit_glyph']} {asp['transit_name']}"))
                asp_item = QTableWidgetItem(f"{asp['aspect_glyph']} {asp['aspect_name']}")
                asp_item.setForeground(QColor(asp.get("color_hex", styles.ACCENT)))
                self.table_transits.setItem(row, 1, asp_item)
                self.table_transits.setItem(row, 2, QTableWidgetItem(f"{asp['natal_glyph']} {asp['natal_name']}"))
                self.table_transits.setItem(row, 3, QTableWidgetItem(asp["formatted_orb"]))

        except Exception as e:
            print("Transit Fehler:", e)

    # ========================================================
    # Synastrie
    # ========================================================

    def _update_synastry(self):
        d_b = self.edit_date_b.date()
        t_b = self.edit_time_b.time()
        req_b = {
            "name": self.edit_name_b.text(),
            "year": d_b.year(),
            "month": d_b.month(),
            "day": d_b.day(),
            "hour": t_b.hour(),
            "minute": t_b.minute(),
            "second": 0,
            "timezone_offset": self.spin_tz_b.value(),
            "latitude": self.spin_lat_b.value(),
            "longitude": self.spin_lon_b.value(),
            "location_name": self.edit_city_b.text(),
            "house_system": "Placidus",
        }

        req = {
            "person_a": self._get_request_dict(),
            "person_b": req_b,
        }

        try:
            res = self.backend.calculate_synastry(req)
            self.transit_data = res["chart_b"]
            self.chart_wheel.set_data(self.chart_data, self.transit_data, "synastry")
            self._render_interpretations(res.get("compatibility_notes", []))
            self.tabs.setCurrentIndex(4)
        except Exception as e:
            QMessageBox.critical(self, "Synastrie-Fehler", str(e))

    # ========================================================
    # Modus Steuerung
    # ========================================================

    def _on_mode_combo_changed(self, index):
        mode = self.combo_mode.itemData(index)
        self._set_mode(mode)

    def _set_mode(self, mode):
        self.mode = mode
        idx = self.combo_mode.findData(mode)
        if idx >= 0:
            self.combo_mode.blockSignals(True)
            self.combo_mode.setCurrentIndex(idx)
            self.combo_mode.blockSignals(False)

        if mode == "transit":
            self.box_transit.setVisible(True)
            self.box_synastry.setVisible(False)
            self.tabs.setTabVisible(5, True)
            self.tabs.setCurrentIndex(5)
            self._update_transits()
        elif mode == "synastry":
            self.box_transit.setVisible(False)
            self.box_synastry.setVisible(True)
            self.tabs.setTabVisible(5, False)
            self._update_synastry()
        else:
            self.box_transit.setVisible(False)
            self.box_synastry.setVisible(False)
            self.tabs.setTabVisible(5, False)
            self.chart_wheel.set_data(self.chart_data, None, "radix")

    def _set_now(self):
        now = datetime.now()
        self.edit_name.setText("Aktueller Moment")
        self.edit_date.setDate(QDate(now.year, now.month, now.day))
        self.edit_time.setTime(QTime(now.hour, now.minute))
        self._calculate_current()

    # ========================================================
    # Export & Über
    # ========================================================

    def _export_svg(self):
        req = self._get_request_dict()
        try:
            svg_text = self.backend.export_svg(req)
            filename, _ = QFileDialog.getSaveFileName(
                self, "Horoskop als SVG exportieren",
                f"{req['name']}_Radix.svg", "SVG Vektorgrafik (*.svg)"
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(svg_text)
                self.statusBar().showMessage(f"SVG erfolgreich gespeichert unter {filename}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Exportfehler", str(e))

    def _show_about(self):
        QMessageBox.about(
            self,
            "Über Astrorust",
            "<h3>✨ Astrorust</h3>"
            "<p><b>Professionelle Astrologie- und Ephemeriden-Software</b></p>"
            "<p>Entwickelt in <b>Rust</b> und nativer <b>Qt6</b>-Oberfläche nach dem Breeze-Dark-Design des Linux Media Encoders.</p>"
            "<p><b>Features & KI-Integration:</b><br>"
            "• Swiss Ephemeris 2.10 (Moshier & Kepler Algorithmen)<br>"
            "• Gestochen scharfes QPainter Horoskop-Rad<br>"
            "• Multi-Provider KI-Deutungen (Claude CLI, Codex CLI, Ollama, API-Keys, GenOffice-Import)<br>"
            "• Zeitschieber &amp; Transitanalyse</p>"
        )
