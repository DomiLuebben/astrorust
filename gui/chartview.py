# -*- coding: utf-8 -*-
"""
Astrorust — ChartView: ein komplettes Horoskop-Fenster (Eingabe, Rad, Tabellen, Analyse, Prognose,
Synastrie, Vedisch, Karte, KI-Deutung). Das Hauptfenster hält davon beliebig viele in Tabs.
"""

import json
import copy
import os
import re
import time
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QSize, QDate, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QGroupBox, QSplitter,
    QTabWidget, QTableWidget, QTableWidgetItem, QProgressBar, QTextEdit, QFileDialog, QMessageBox, QScrollArea,
    QFrame, QApplication, QCheckBox, QHeaderView,
)

import styles
from ai_engine import AiConfig, AiGenerationWorker, MODULE_NEEDS, retain_worker
from ai_dialog import AiSettingsDialog
from analysis_tab import AnalysisPanel
from astromap_tab import AstroMapPanel
from chart_wheel import ChartWheelWidget
from forecast_tab import ForecastPanel, tp_from_qdate, WaitCursor
from i18n import tr, language
from pdf_export import build_report_html, export_pdf, render_wheel_image, table_html
from synastry_tab import SynastryPanel
from vedic_tab import VedicPanel
from widgets import PersonInput, compact_combo, make_table, set_rows, esc

READINGS_DIR = os.path.expanduser("~/.local/share/astrorust/readings")

PARTNER_DEFAULT = {"name": "Mileva Marić", "year": 1875, "month": 12, "day": 19, "hour": 12, "minute": 0,
                   "location_name": "Titel, Serbien", "latitude": 45.2056, "longitude": 20.0944,
                   "timezone": "Europe/Belgrade", "timezone_offset": 1.0}

EINSTEIN_DEFAULT = {"name": "Albert Einstein", "year": 1879, "month": 3, "day": 14, "hour": 11, "minute": 30,
                    "location_name": "Ulm, Deutschland", "latitude": 48.4011, "longitude": 9.9876,
                    "timezone": "Europe/Berlin", "timezone_offset": 0.67}


class ChartView(QWidget):
    statusMessage = pyqtSignal(str)
    titleChanged = pyqtSignal(str)
    openDatabase = pyqtSignal()
    settingsChanged = pyqtSignal()

    def __init__(self, backend, settings, store, profile=None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.settings = settings
        self.store = store
        self.chart = None
        self._natal_request = None
        self._profile_id = (profile or {}).get("id")
        self.synastry = None
        self.overlays = {}      # kind -> {"chart", "aspects", "label"}
        self.wheel_kind = "radix"
        self.ai_worker = None
        self._retired = []
        self.ai_cfg = AiConfig.load()
        self._ai_text = ""
        self._ai_dirty = False
        self._ai_timer = QTimer(self)
        self._ai_timer.setInterval(150)
        self._ai_timer.timeout.connect(self._flush_ai_text)

        self._build_ui(profile or EINSTEIN_DEFAULT)

    # ─────────────────────── Aufbau ───────────────────────
    def _build_ui(self, profile):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._left_panel(profile))
        splitter.addWidget(self._center_panel())
        splitter.addWidget(self._right_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([380, 500, 470])
        outer.addWidget(splitter)
        self._splitter = splitter

    def _left_panel(self, profile):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(372)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        box = QGroupBox(tr("Profile"))
        v = QVBoxLayout(box)
        self.combo_profiles = compact_combo(QComboBox())
        self.combo_profiles.activated.connect(self._on_profile_chosen)
        v.addWidget(self.combo_profiles)
        row = QHBoxLayout()
        b = QPushButton(tr("💾 Speichern"))
        b.setToolTip(tr("Aktuell eingetragene Daten als Profil speichern"))
        b.clicked.connect(self.save_profile)
        row.addWidget(b)
        b = QPushButton(tr("📚 Datenbank…"))
        b.setToolTip(tr("Horoskop-Datenbank: suchen, gruppieren, importieren, exportieren"))
        b.clicked.connect(self.openDatabase.emit)
        row.addWidget(b)
        v.addLayout(row)
        lay.addWidget(box)

        self.person_a = PersonInput(tr("Geburtsdaten (Radix)"), self.backend, profile, with_houses=True)
        self.person_a.set_profile(profile)
        if self.person_a.combo_houses is not None:
            i = self.person_a.combo_houses.findText(self.settings.house_system)
            if i >= 0 and "house_system" not in profile:
                self.person_a.combo_houses.setCurrentIndex(i)
        lay.addWidget(self.person_a)

        self.box_partner = QGroupBox(tr("Partner / Person B (Synastrie)"))
        self.box_partner.setCheckable(True)
        self.box_partner.setChecked(False)
        pv = QVBoxLayout(self.box_partner)
        pv.setContentsMargins(4, 14, 4, 4)
        self.person_b = PersonInput("", self.backend, PARTNER_DEFAULT, with_houses=False)
        self.person_b.setFlat(True)
        self.person_b.setStyleSheet("QGroupBox { border: none; margin: 0; padding: 0; }")
        pv.addWidget(self.person_b)
        self.box_partner.toggled.connect(self.person_b.setVisible)
        self.person_b.setVisible(False)
        lay.addWidget(self.box_partner)

        box = QGroupBox(tr("Radanzeige"))
        v = QVBoxLayout(box)
        self.combo_wheel = compact_combo(QComboBox())
        self.combo_wheel.activated.connect(self._on_wheel_chosen)
        v.addWidget(self.combo_wheel)
        lay.addWidget(box)
        self._refresh_wheel_combo()

        b = QPushButton(tr("⚡ Berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.calculate)
        lay.addWidget(b)
        lay.addStretch()
        scroll.setWidget(container)
        self.refresh_profiles()
        return scroll

    def _center_panel(self):
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)

        head = QFrame()
        head.setStyleSheet(f"background: {styles.SURFACE_RAISED}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 6px; padding: 6px;")
        h = QHBoxLayout(head)
        h.setContentsMargins(6, 4, 6, 4)
        v = QVBoxLayout()
        self.lbl_name = QLabel("")
        self.lbl_name.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_name.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {styles.TEXT};")
        v.addWidget(self.lbl_name)
        self.lbl_meta = QLabel("")
        self.lbl_meta.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_meta.setWordWrap(True)
        self.lbl_meta.setMinimumHeight(34)
        self.lbl_meta.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
        v.addWidget(self.lbl_meta)
        h.addLayout(v, 1)
        leg = QHBoxLayout()
        leg.setSpacing(10)
        for name, color in [(tr("Feuer"), styles.COLOR_FIRE), (tr("Erde"), styles.COLOR_EARTH), (tr("Luft"), styles.COLOR_AIR), (tr("Wasser"), styles.COLOR_WATER)]:
            dot = QLabel(f"<span style='color:{color}; font-size:14px;'>●</span> {name}")
            dot.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
            leg.addWidget(dot)
        h.addLayout(leg)
        lay.addWidget(head)

        self.wheel = ChartWheelWidget()
        self.wheel.planet_selected.connect(self._on_wheel_planet)
        lay.addWidget(self.wheel, 1)

        bar = QFrame()
        bar.setStyleSheet(f"background: {styles.SURFACE_SUNKEN}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 4px;")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 4, 6, 4)
        self.lbl_angles = {}
        for key in ("asc", "mc", "dc", "ic", "fortune"):
            lbl = QLabel("—")
            lbl.setStyleSheet(f"font-family: monospace; font-size: 11px; color: {styles.ACCENT}; font-weight: bold;")
            bl.addWidget(lbl)
            bl.addStretch()
            self.lbl_angles[key] = lbl
        lay.addWidget(bar)
        return container

    def _right_panel(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Horoskop
        self.sub_chart = QTabWidget()
        self.table_planets = make_table(["Pt", "Planet", "Position", "H", "Würde", "Rx"], stretch_col=2)
        self.sub_chart.addTab(self.table_planets, tr("Planeten"))
        tab_asp = QWidget()
        va = QVBoxLayout(tab_asp)
        va.setContentsMargins(4, 4, 4, 4)
        self.table_aspects = QTableWidget()
        self.table_aspects.cellClicked.connect(self._on_aspect_cell)
        va.addWidget(self.table_aspects, 1)
        self.lbl_aspect = QLabel(tr("Klicken Sie auf ein Feld im Aspektarium für Details."))
        self.lbl_aspect.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED}; background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px;")
        va.addWidget(self.lbl_aspect)
        self.sub_chart.addTab(tab_asp, tr("Aspektarium"))
        self.table_houses = make_table(["Haus", "Cusp", "Zeichen", "Position"], stretch_col=2)
        self.sub_chart.addTab(self.table_houses, tr("Häuser"))
        self.tab_elements = QWidget()
        self.l_elem = QVBoxLayout(self.tab_elements)
        self.l_elem.setContentsMargins(12, 12, 12, 12)
        self.sub_chart.addTab(self.tab_elements, tr("Elemente"))
        self.text_rules = QTextEdit()
        self.text_rules.setReadOnly(True)
        self.sub_chart.addTab(self.text_rules, tr("Regel-Deutung"))
        self.tabs.addTab(self.sub_chart, tr("Horoskop"))

        # Analyse
        self.analysis = AnalysisPanel()
        self.tabs.addTab(self.analysis, tr("Analyse"))

        # Prognose
        self.forecast = ForecastPanel(self.backend, self.analysis_request, self.display_zone)
        self.forecast.overlayChanged.connect(self._on_overlay)
        self.forecast.status.connect(self.statusMessage.emit)
        self.tabs.addTab(self.forecast, tr("Prognose"))

        # Synastrie
        syn = QWidget()
        sv = QVBoxLayout(syn)
        sv.setContentsMargins(4, 4, 4, 4)
        row = QHBoxLayout()
        b = QPushButton(tr("Partnervergleich berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.calculate_synastry)
        row.addWidget(b)
        self.lbl_syn_hint = QLabel(tr("Daten von Person B links unter „Partner / Person B“ eintragen."))
        self.lbl_syn_hint.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        row.addWidget(self.lbl_syn_hint, 1)
        sv.addLayout(row)
        self.syn_panel = SynastryPanel()
        self.syn_panel.showChart.connect(self._on_syn_chart)
        sv.addWidget(self.syn_panel, 1)
        self.tabs.addTab(syn, tr("Synastrie"))

        # Vedisch / Karte
        self.vedic = VedicPanel(self.backend, self.analysis_request)
        self.tabs.addTab(self.vedic, tr("Vedisch"))
        self.astromap = AstroMapPanel(self.backend, self.analysis_request)
        self.tabs.addTab(self.astromap, tr("Karte"))

        # KI
        self.tabs.addTab(self._ai_tab(), tr("🔮 KI-Deutung"))
        return self.tabs

    # ─────────────────────── Eingaben ───────────────────────
    def request_a(self, **settings_overrides) -> dict:
        return self.person_a.request(self.settings.calc_settings(**settings_overrides),
                                     self.person_a.combo_houses.currentText())

    def request_b(self) -> dict:
        return self.person_b.request(self.settings.calc_settings(analysis=False, fixed_stars=False),
                                     self.person_a.combo_houses.currentText())

    def display_zone(self):
        return self.person_a.zone() or None

    def analysis_request(self):
        """Synchronize all derived views with the data currently entered."""
        request = self.request_a()
        if request != self._natal_request:
            if not self.calculate():
                raise ValueError(tr("Berechnungsfehler"))
        return copy.deepcopy(self._natal_request)

    def _clear_derived(self):
        self.forecast.clear_results()
        self.vedic.clear_results()
        self.astromap.clear_results()
        self.syn_panel.clear_results()
        self.cancel_ai()
        self._ai_text = ""
        self._ai_dirty = False
        self.text_ai.clear()

    # ─────────────────────── Berechnen ───────────────────────
    def calculate(self):
        if not self.person_a.is_valid():
            QMessageBox.warning(self, tr("Ungültiges Datum"),
                                f"{tr('Geburtsdatum')}: „{self.person_a.edit_date.text()}“\n{tr('Erlaubt sind JJJJ-MM-TT oder TT.MM.JJJJ.')}")
            self.person_a.edit_date.setFocus()
            return False
        try:
            with WaitCursor():
                request = self.request_a()
                chart = self.backend.call("chart", request)
        except Exception as e:
            QMessageBox.critical(self, tr("Berechnungsfehler"), str(e))
            return False
        self.chart = chart
        self._natal_request = copy.deepcopy(request)
        self._clear_derived()
        # Ergebnisse, die auf dem alten Radix beruhen, verwerfen
        self.overlays.clear()
        self.synastry = None
        self.wheel_kind = "radix"
        self._render_chart()
        self._refresh_wheel_combo()
        self._show_wheel()
        self.titleChanged.emit(self.chart["name"])
        self._refresh_history()
        self.forecast.update_transits(activate=False)
        if self.box_partner.isChecked():
            self.calculate_synastry(switch_tab=False)
        self.statusMessage.emit(f"{tr('Horoskop für')} {self.chart['name']} {tr('berechnet')} (JD {self.chart['julian_day']:.4f})")
        return True

    def calculate_synastry(self, switch_tab=True):
        if not self.box_partner.isChecked():
            self.box_partner.setChecked(True)
        if not self.person_b.is_valid():
            QMessageBox.warning(self, tr("Ungültiges Datum"), tr("Datum von Person B ist ungültig."))
            return
        try:
            with WaitCursor():
                request = self.request_a()
                if request != self._natal_request and not self.calculate():
                    return
                self.synastry = self.backend.call("synastry", {"person_a": request, "person_b": self.request_b()})
        except Exception as e:
            QMessageBox.critical(self, tr("Synastrie-Fehler"), str(e))
            return
        self.syn_panel.render(self.synastry)
        self.overlays["partner"] = {"chart": self.synastry["chart_b"], "aspects": self.synastry["cross_aspects"],
                                    "label": self.synastry["chart_b"]["name"]}
        if self.synastry.get("composite_chart"):
            self.overlays["composite"] = {"chart": self.synastry["composite_chart"], "aspects": [], "label": ""}
        if self.synastry.get("davison_chart"):
            self.overlays["davison"] = {"chart": self.synastry["davison_chart"], "aspects": [], "label": ""}
        self._refresh_wheel_combo()
        self.wheel_kind = "partner"
        self._show_wheel()
        if switch_tab:
            self.tabs.setCurrentIndex(3)

    # ─────────────────────── Rad ───────────────────────
    WHEEL_LABELS = [
        ("radix", "☉ Radix"), ("transit", "⏳ Transit"), ("progression", "➚ Progression / Solarbogen"),
        ("return", "↺ Return"), ("partner", "👥 Radix + Partner"), ("composite", "◐ Composite"), ("davison", "◑ Davison"),
    ]

    def _refresh_wheel_combo(self):
        self.combo_wheel.blockSignals(True)
        self.combo_wheel.clear()
        for kind, label in self.WHEEL_LABELS:
            if kind == "radix" or kind in self.overlays:
                self.combo_wheel.addItem(tr(label), kind)
        i = self.combo_wheel.findData(self.wheel_kind)
        self.combo_wheel.setCurrentIndex(max(0, i))
        self.combo_wheel.blockSignals(False)

    def _on_wheel_chosen(self, index):
        self.wheel_kind = self.combo_wheel.itemData(index)
        self._show_wheel()

    def _show_wheel(self):
        if not self.chart:
            self.wheel.set_data(None)
            return
        kind = self.wheel_kind
        ov = self.overlays.get(kind)
        if kind in ("composite", "davison") and ov:
            self.wheel.set_data(ov["chart"], None, "radix")
            self.lbl_name.setText(ov["chart"]["name"])
            self.lbl_meta.setText(f"{ov['chart']['date_time']} • {ov['chart']['location_name']} • {ov['chart']['house_system']}")
        elif kind != "radix" and ov:
            self.wheel.set_data(self.chart, ov["chart"], "synastry" if kind == "partner" else "transit", ov["aspects"], ov["label"])
            self._set_header(self.chart)
        else:
            self.wheel.set_data(self.chart, None, "radix")
            self._set_header(self.chart)
        shown = ov["chart"] if kind in ("composite", "davison") and ov else self.chart
        for key, field in [("asc", "ascendant"), ("mc", "midheaven"), ("dc", "descendant"), ("ic", "imum_coeli"), ("fortune", "part_of_fortune")]:
            prefix = {"asc": "AC", "mc": "MC", "dc": "DC", "ic": "IC", "fortune": "⊗"}[key]
            self.lbl_angles[key].setText(f"{prefix}: {shown['angles'][field + '_formatted']}")

    def _set_header(self, c):
        self.lbl_name.setText(c["name"])
        extra = f" • {tr('siderisch')} ({c.get('ayanamsa_name')})" if c.get("zodiac") == "Sidereal" else ""
        self.lbl_meta.setText(f"{c['date_time']} • {c['location_name']} • {tr('Häuser')}: {c['house_system']}{extra}")

    def _on_overlay(self, kind, chart, aspects, label):
        self.overlays[kind] = {"chart": chart, "aspects": aspects, "label": label}
        self.wheel_kind = kind
        self._refresh_wheel_combo()
        self._show_wheel()

    def _on_syn_chart(self, kind, chart):
        self.overlays[kind] = {"chart": chart, "aspects": [], "label": ""}
        self.wheel_kind = kind
        self._refresh_wheel_combo()
        self._show_wheel()

    def _on_wheel_planet(self, planet):
        for row in range(self.table_planets.rowCount()):
            item = self.table_planets.item(row, 1)
            if item and item.text() == planet.get("name"):
                self.table_planets.selectRow(row)
                self.tabs.setCurrentIndex(0)
                self.sub_chart.setCurrentIndex(0)
                break

    # ─────────────────────── Darstellung ───────────────────────
    DIGNITY_COLORS = None

    def _render_chart(self):
        c = self.chart
        self._set_header(c)
        ang = c["angles"]
        self.lbl_angles["asc"].setText(f"AC: {ang['ascendant_formatted']}")
        self.lbl_angles["mc"].setText(f"MC: {ang['midheaven_formatted']}")
        self.lbl_angles["dc"].setText(f"DC: {ang['descendant_formatted']}")
        self.lbl_angles["ic"].setText(f"IC: {ang['imum_coeli_formatted']}")
        self.lbl_angles["fortune"].setText(f"⊗: {ang['part_of_fortune_formatted']}")

        rows, colors = [], {}
        for i, p in enumerate(c["planets"]):
            dig = p.get("dignity") or "—"
            rows.append([p["glyph"], p["name"], f"{p['formatted_deg']} {p['sign_glyph']}", f"{p['house']}.", dig,
                         "℞" if p["is_retrograde"] else "•"])
            if dig in ("Domizil", "Domicile"):
                colors[(i, 4)] = styles.COLOR_EARTH
            elif dig in ("Erhöhung", "Exaltation"):
                colors[(i, 4)] = styles.COLOR_AIR
            elif dig in ("Fall", "Exil", "Detriment"):
                colors[(i, 4)] = styles.STOP_RED
            if p["is_retrograde"]:
                colors[(i, 5)] = styles.STOP_RED
        set_rows(self.table_planets, rows, colors)

        self._render_aspectarium(c["planets"], c["aspects"])
        names = {1: "AC", 4: "IC", 7: "DC", 10: "MC"}
        set_rows(self.table_houses, [[f"{tr('Haus')} {h['house_number']}", names.get(h["house_number"], ""),
                                      f"{h['sign_glyph']} {h['sign_name']}", h["formatted_deg"]] for h in c["houses"]])
        self._render_elements(c["element_quality"])
        html = ""
        for sec in c.get("interpretations", []):
            html += f"<h3 style='color:{styles.ACCENT}; margin-bottom:2px;'>{esc(sec.get('title'))}</h3>"
            html += f"<div style='color:{styles.TEXT_MUTED}; font-size:10px; text-transform:uppercase;'>{esc(sec.get('subtitle'))}</div>"
            html += f"<p style='margin-top:4px; line-height:1.4;'>{esc(sec.get('text'))}</p>"
            html += f"<div style='color:{styles.COLOR_AIR}; font-size:10px; margin-bottom:12px;'>{tr('Schlagwörter')}: {esc(' • '.join(sec.get('keywords', [])))}</div><hr>"
        self.text_rules.setHtml(html)
        self.analysis.render(c)

    def _render_aspectarium(self, planets, aspects):
        n = len(planets)
        self.table_aspects.clear()
        self.table_aspects.setRowCount(n)
        self.table_aspects.setColumnCount(n)
        headers = [p["glyph"] for p in planets]
        self.table_aspects.setHorizontalHeaderLabels(headers)
        self.table_aspects.setVerticalHeaderLabels(headers)
        lookup = {}
        for a in aspects:
            lookup[(a["point_a"], a["point_b"])] = a
            lookup[(a["point_b"], a["point_a"])] = a
        for r in range(n):
            for col in range(n):
                if col < r:
                    asp = lookup.get((planets[r]["id"], planets[col]["id"]))
                    item = QTableWidgetItem(asp["aspect_glyph"] if asp else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if asp:
                        item.setForeground(QColor(asp.get("color_hex", styles.ACCENT)))
                        item.setData(Qt.ItemDataRole.UserRole, asp)
                else:
                    item = QTableWidgetItem("")
                    item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.table_aspects.setItem(r, col, item)
        self.table_aspects.resizeColumnsToContents()
        self.table_aspects.resizeRowsToContents()

    def _on_aspect_cell(self, row, col):
        item = self.table_aspects.item(row, col)
        asp = item.data(Qt.ItemDataRole.UserRole) if item else None
        if asp:
            self.lbl_aspect.setText(
                f"<b>{esc(asp['point_a_name'])} {asp['aspect_glyph']} {esc(asp['aspect_name'])} {esc(asp['point_b_name'])}</b><br>"
                f"{tr('Exakter Winkel')}: {asp['actual_angle']:.2f}° ({tr('Soll')}: {asp['target_angle']:.1f}°) • {tr('Orbis')}: {asp['formatted_orb']}<br>"
                f"{tr('Status')}: {tr('Applikativ (zunehmend)') if asp.get('is_applying') else tr('Separativ (abnehmend)')}")

    def _render_elements(self, eq):
        while self.l_elem.count():
            it = self.l_elem.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        tot_e = max(1, eq.get("fire", 0) + eq.get("earth", 0) + eq.get("air", 0) + eq.get("water", 0))
        tot_q = max(1, eq.get("cardinal", 0) + eq.get("fixed", 0) + eq.get("mutable", 0))

        def block(title, items, total):
            box = QGroupBox(title)
            l = QVBoxLayout(box)
            for name, val, col in items:
                h = QHBoxLayout()
                h.addWidget(QLabel(f"{name}:"))
                p = QProgressBar()
                p.setRange(0, total)
                p.setValue(val)
                p.setStyleSheet(f"QProgressBar::chunk {{ background-color: {col}; }}")
                h.addWidget(p)
                h.addWidget(QLabel(str(val)))
                l.addLayout(h)
            self.l_elem.addWidget(box)

        block(f"{tr('Vier Elemente')} ({tr('Dominant')}: {eq.get('dominant_element', '—')})",
              [(tr("Feuer"), eq.get("fire", 0), styles.COLOR_FIRE), (tr("Erde"), eq.get("earth", 0), styles.COLOR_EARTH),
               (tr("Luft"), eq.get("air", 0), styles.COLOR_AIR), (tr("Wasser"), eq.get("water", 0), styles.COLOR_WATER)], tot_e)
        block(f"{tr('Drei Qualitäten')} ({tr('Dominant')}: {eq.get('dominant_quality', '—')})",
              [(tr("Kardinal"), eq.get("cardinal", 0), styles.ACCENT), (tr("Fix"), eq.get("fixed", 0), styles.COLOR_AIR),
               (tr("Veränderlich"), eq.get("mutable", 0), "#a855f7")], tot_q)
        note = QLabel(tr("Gezählt werden die zehn Planeten von Sonne bis Pluto und der Aszendent."))
        note.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        self.l_elem.addWidget(note)
        self.l_elem.addStretch()

    # ─────────────────────── Profile ───────────────────────
    def refresh_profiles(self):
        self.combo_profiles.blockSignals(True)
        self.combo_profiles.clear()
        if not self.store.profiles:
            self.combo_profiles.addItem(tr("(Keine Profile gespeichert)"), None)
        for p in sorted(self.store.profiles, key=lambda x: x.get("name", "").lower()):
            self.combo_profiles.addItem(p["name"], p["id"])
        self.combo_profiles.setCurrentIndex(-1)
        self.combo_profiles.blockSignals(False)

    def _on_profile_chosen(self, index):
        ident = self.combo_profiles.itemData(index)
        p = next((x for x in self.store.profiles if x["id"] == ident), None)
        if p:
            self.load_profile(p)

    def load_profile(self, p, partner=False):
        if partner:
            self.box_partner.setChecked(True)
            self.person_b.set_profile(p)
            self.calculate_synastry()
        else:
            self._profile_id = p.get("id")
            self.person_a.set_profile(p)
            self.calculate()

    def save_profile(self):
        if not self.person_a.is_valid():
            QMessageBox.warning(self, tr("Ungültiges Datum"), tr("Erlaubt sind JJJJ-MM-TT oder TT.MM.JJJJ."))
            return
        p = self.person_a.profile()
        if self._profile_id:
            p["id"] = self._profile_id
        if not self.person_a.edit_name.text().strip():
            self.person_a.edit_name.setText(tr("Mein Profil"))
            p = self.person_a.profile()
        if self._profile_id:
            p["id"] = self._profile_id
        saved = self.store.upsert(p)
        self._profile_id = saved["id"]
        self.refresh_profiles()
        self.statusMessage.emit(f"{tr('Profil')} „{saved['name']}“ {tr('gespeichert')}")

    def set_now(self):
        """Jetzt: aktuelle Ortszeit des Rechners mit passendem UTC-Offset (inkl. Sommerzeit)."""
        now = datetime.now().astimezone()
        off = now.utcoffset().total_seconds() / 3600.0 if now.utcoffset() else 0.0
        a = self.person_a
        self._profile_id = None
        a.edit_name.setText(tr("Aktueller Moment"))
        a.edit_date.setDate(QDate(now.year, now.month, now.day))
        from PyQt6.QtCore import QTime
        a.edit_time.setTime(QTime(now.hour, now.minute))
        a.set_zone("")           # Ortszeit des Rechners → manueller Offset
        a.spin_tz.setValue(off)
        self.calculate()

    # ─────────────────────── Export ───────────────────────
    def export_svg(self):
        if not self.person_a.is_valid():
            return
        req = self.request_a()
        try:
            svg_text = self.backend.call("svg", req)
        except Exception as e:
            QMessageBox.critical(self, tr("Exportfehler"), str(e))
            return
        safe = re.sub(r'[\\/:*?"<>|]+', "_", req["name"]).strip() or "Horoskop"
        fn, _ = QFileDialog.getSaveFileName(self, tr("Horoskop als SVG exportieren"), f"{safe}_Radix.svg", "SVG (*.svg)")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(svg_text)
            self.statusMessage.emit(f"{tr('SVG gespeichert unter')} {fn}")

    def export_pdf(self):
        try:
            self.analysis_request()
        except ValueError:
            return
        safe = re.sub(r'[\\/:*?"<>|]+', "_", self.chart["name"]).strip() or "Horoskop"
        fn, _ = QFileDialog.getSaveFileName(self, tr("PDF-Bericht speichern"), f"{safe}.pdf", "PDF (*.pdf)")
        if not fn:
            return
        sections = []
        a = self.chart.get("analysis")
        if a:
            sections.append((tr("Klassische Würden"), table_html(
                [tr("Planet"), tr("Zeichen"), tr("Wertung"), tr("Zustand")],
                [[f"{d['glyph']} {d['planet_name']}", d["sign_name"], f"{d['score']:+d}", d["summary"]] for d in a["dignities"]])))
            if a["patterns"]:
                sections.append((tr("Aspektfiguren"), table_html([tr("Figur"), tr("Beteiligte"), tr("Bedeutung")],
                                                              [[p["name"], p["glyphs"], p["description"]] for p in a["patterns"]])))
            if a["lots"]:
                sections.append((tr("Arabische Lose"), table_html([tr("Los"), tr("Position"), tr("Haus")],
                                                                [[l["name"], f"{l['formatted']} {l['sign_name']}", f"{l['house']}."] for l in a["lots"]])))
            if a["fixed_stars"]:
                sections.append((tr("Fixsterne"), table_html([tr("Stern"), tr("Kontakt"), tr("Orbis")],
                                                           [[s["star"], f"{s['contact_glyph']} {s['contact']}", s["formatted_orb"]] for s in a["fixed_stars"]])))
            if a["midpoint_hits"]:
                sections.append((tr("Halbsummenbilder"), table_html([tr("Bild"), tr("Orbis")],
                                                                  [[h["label"], h["formatted_orb"]] for h in a["midpoint_hits"][:25]])))
        if self.synastry:
            sections.append((tr("Synastrie"), table_html([tr("A"), tr("Aspekt"), tr("B"), tr("Orbis")],
                                                       [[f"{x['transit_glyph']} {x['transit_name']}", f"{x['aspect_glyph']} {x['aspect_name']}",
                                                         f"{x['natal_glyph']} {x['natal_name']}", x["formatted_orb"]] for x in self.synastry["cross_aspects"][:40]])))
        ai = self._ai_text.strip() or None
        try:
            img = render_wheel_image(self.wheel, chart=self.chart)
            html = build_report_html(self.chart, img, sections, ai)
            export_pdf(fn, html, self.chart["name"])
        except Exception as e:
            QMessageBox.critical(self, tr("Exportfehler"), str(e))
            return
        self.statusMessage.emit(f"{tr('PDF gespeichert unter')} {fn}")

    # ─────────────────────── KI ───────────────────────
    def _ai_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QFrame()
        top.setStyleSheet(f"background: {styles.SURFACE_SUNKEN}; border: 1px solid {styles.BORDER_SOFT}; border-radius: 5px; padding: 6px;")
        v = QVBoxLayout(top)
        v.setContentsMargins(4, 4, 4, 4)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Thema:")))
        self.combo_ai = QComboBox()
        for key, label in [
            ("gesamt", "🌟 Großes Radix-Persönlichkeitsprofil"),
            ("beruf", "🏛️ Berufung, Karriere & Lebensziel (MC & Haus 10)"),
            ("partnerschaft", "💖 Partnerschaft, Liebe & Beziehung (Venus, Mars & Haus 7)"),
            ("seelenleben", "🌙 Seelenleben & emotionale Wurzeln (Mond & Haus 4)"),
            ("karma", "🪐 Karma, Seelenplan & Schattenarbeit (Saturn, Chiron, Knoten)"),
            ("transite", "⏳ Aktuelle Transite & Zeitqualität (Jahresvorschau)"),
            ("progression", "➚ Progression / Solarbogen (Entwicklungsphase)"),
            ("solarreturn", "↺ Return-Horoskop (Solar-/Lunar-Return)"),
            ("synastrie", "👥 Partnervergleich & Beziehungsdynamik (Synastrie, Composite)"),
            ("vedisch", "🕉 Vedische Deutung (Nakshatra, Dasha, Navamsa)"),
            ("astrokarte", "🗺 Astrokartografie (Orte & Planetenlinien)"),
        ]:
            self.combo_ai.addItem(tr(label), key)
        row.addWidget(self.combo_ai, 1)
        b = QPushButton(tr("⚙️ Einstellungen"))
        b.setToolTip(tr("KI-Provider, API-Keys oder lokale Modelle konfigurieren"))
        b.clicked.connect(self.open_ai_settings)
        row.addWidget(b)
        v.addLayout(row)
        row = QHBoxLayout()
        self.btn_ai_go = QPushButton(tr("✨ KI-Deutung generieren"))
        self.btn_ai_go.setObjectName("btn_start")
        self.btn_ai_go.clicked.connect(self.generate_ai)
        row.addWidget(self.btn_ai_go, 1)
        self.btn_ai_cancel = QPushButton(tr("⏹ Abbrechen"))
        self.btn_ai_cancel.setEnabled(False)
        self.btn_ai_cancel.clicked.connect(self.cancel_ai)
        row.addWidget(self.btn_ai_cancel)
        v.addLayout(row)
        layout.addWidget(top)

        self.lbl_ai = QLabel(tr("Bereit zur KI-Generierung."))
        self.lbl_ai.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
        layout.addWidget(self.lbl_ai)
        self.progress_ai = QProgressBar()
        self.progress_ai.setRange(0, 0)
        self.progress_ai.setVisible(False)
        layout.addWidget(self.progress_ai)

        self.text_ai = QTextEdit()
        self.text_ai.setReadOnly(True)
        self.text_ai.setPlaceholderText(tr("Die generierte astrologische Deutung erscheint hier in vollständigem Markdown…"))
        layout.addWidget(self.text_ai, 1)

        row = QHBoxLayout()
        for label, slot in [(tr("📋 Kopieren"), self.copy_ai), (tr("💾 Als Text speichern"), self.save_ai_as)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch()
        row.addWidget(QLabel(tr("Verlauf:")))
        self.combo_history = QComboBox()
        self.combo_history.setMinimumWidth(180)
        self.combo_history.activated.connect(self._open_history)
        row.addWidget(self.combo_history)
        layout.addLayout(row)
        self._refresh_history()
        return container

    def open_ai_settings(self):
        dlg = AiSettingsDialog(self)
        if dlg.exec():
            self.ai_cfg = AiConfig.load()
            self.lbl_ai.setText(f"{tr('Aktiver KI-Provider aktualisiert')}: {self.ai_cfg.get('active_provider', 'auto')}")

    def focus_ai_tab(self):
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def _gather_extras(self, module):
        """Daten, die ein Thema zusätzlich braucht – wenn nötig, werden sie jetzt berechnet."""
        need = MODULE_NEEDS.get(module)
        extras = {}
        try:
            if need == "transit":
                if self.wheel_kind == "transit" and self.forecast.last_transit:
                    tr_res = self.forecast.last_transit      # der im Zeitschieber gewählte Zeitpunkt
                else:
                    now = datetime.now(timezone.utc)
                    tr_res = self.backend.call("transit", {
                        "natal": self.request_a(), "transit_year": now.year, "transit_month": now.month, "transit_day": now.day,
                        "transit_hour": now.hour, "transit_minute": now.minute, "transit_timezone_offset": 0.0})
                extras["transit"] = tr_res["transit_chart"]
                extras["transit_aspects"] = tr_res["transit_aspects"]
            elif need == "partner":
                if self.box_partner.isChecked():
                    self.calculate_synastry(switch_tab=False)
                if not self.synastry:
                    if not self.box_partner.isChecked():
                        QMessageBox.information(self, tr("Partnerdaten fehlen"),
                                                tr("Für den Partnervergleich bitte „Partner / Person B“ aktivieren, Daten eintragen und berechnen."))
                        return None
                    self.calculate_synastry(switch_tab=False)
                    if not self.synastry:
                        return None
                extras.update({"partner": self.synastry["chart_b"], "cross_aspects": self.synastry["cross_aspects"],
                               "composite": self.synastry.get("composite_chart"), "davison": self.synastry.get("davison_chart")})
            elif need == "progression":
                res = self.forecast.last_progression
                if res is None:
                    today = QDate.currentDate()
                    res = self.backend.call("progression", {"natal": self.request_a(), "target": tp_from_qdate(today, 12), "kind": "secondary"})
                extras["progression"] = res
            elif need == "return":
                res = self.forecast.last_return
                if res is None:
                    today = QDate.currentDate()
                    res = self.backend.call("return", {"natal": self.request_a(), "body": "Sun", "start": tp_from_qdate(QDate(today.year(), 1, 1)),
                                                       "display_timezone": self.display_zone()})
                extras["return"] = res
            elif need == "vedic":
                self.vedic.run()
                if not self.vedic.res:
                    return None
                extras["vedic"] = self.vedic.res
            elif need == "astromap":
                self.astromap.run()
                if not self.astromap.res:
                    return None
                extras["astromap"] = self.astromap.res
        except Exception as e:
            QMessageBox.warning(self, tr("Daten fehlen"), str(e))
            return None
        return extras

    def generate_ai(self):
        try:
            self.analysis_request()
        except ValueError as e:
            QMessageBox.warning(self, tr("Berechnungsfehler"), str(e))
            return
        if not self.chart:
            QMessageBox.warning(self, tr("Hinweis"), tr("Bitte zuerst ein Horoskop berechnen."))
            return
        self.ai_cfg = AiConfig.load()
        self.cancel_ai()
        module = self.combo_ai.currentData()
        with WaitCursor():
            extras = self._gather_extras(module)
        if extras is None:
            return
        self._ai_text = ""
        self.text_ai.clear()
        self.btn_ai_go.setEnabled(False)
        self.btn_ai_cancel.setEnabled(True)
        self.progress_ai.setVisible(True)
        self.lbl_ai.setText(tr("KI-Modell wird initialisiert…"))
        self._ai_module = module

        w = AiGenerationWorker(self.chart, module, self.ai_cfg, extras, language())
        w.status_signal.connect(self.lbl_ai.setText)
        w.chunk_signal.connect(self._on_ai_chunk)
        w.finished_signal.connect(self._on_ai_done)
        w.error_signal.connect(self._on_ai_error)
        self.ai_worker = w
        self._ai_timer.start()
        w.start()

    def _on_ai_chunk(self, text):
        self._ai_text += text
        self._ai_dirty = True

    def _flush_ai_text(self):
        if self._ai_dirty:
            self._ai_dirty = False
            sb = self.text_ai.verticalScrollBar()
            at_end = sb.value() >= sb.maximum() - 4
            self.text_ai.setMarkdown(self._ai_text)
            if at_end:
                sb.setValue(sb.maximum())

    def _on_ai_done(self, text):
        self._ai_timer.stop()
        self._ai_text = text
        self.text_ai.setMarkdown(text)
        self._reset_ai(tr("Deutung erfolgreich generiert!"))
        self._save_reading(text)

    def _on_ai_error(self, err):
        self._ai_timer.stop()
        self._reset_ai(f"{tr('Fehler')}: {err}")
        QMessageBox.critical(self, tr("KI-Fehler"), f"{tr('Fehler bei der KI-Generierung')}:\n\n{err}\n\n{tr('Prüfen Sie Ihre Einstellungen unter „Einstellungen“.')}")

    def _reset_ai(self, msg):
        self.btn_ai_go.setEnabled(True)
        self.btn_ai_cancel.setEnabled(False)
        self.progress_ai.setVisible(False)
        self.lbl_ai.setText(msg)

    def cancel_ai(self):
        w = self.ai_worker
        if w and w.isRunning():
            w.cancel()
            for sig in (w.status_signal, w.chunk_signal, w.finished_signal, w.error_signal):
                try:
                    sig.disconnect()
                except TypeError:
                    pass
            # QThread nicht mit terminate() abwürgen: er läuft sauber aus, die Referenz bleibt bis dahin.
            self._retired.append(w)
            retain_worker(w)
            self._ai_timer.stop()
            self._reset_ai(tr("Generierung abgebrochen."))
        self._retired = [worker for worker in self._retired if worker.isRunning()]

    def shutdown(self):
        """Beim Schließen: laufende Anfragen beenden."""
        self.cancel_ai()
        for w in [self.ai_worker, *self._retired]:
            if w is not None and w.isRunning():
                w.cancel()
                w.wait(3000)
                if w.isRunning():
                    retain_worker(w)
        self.forecast.transit_timer.stop()

    def copy_ai(self):
        txt = self.text_ai.toPlainText()
        if txt:
            QApplication.clipboard().setText(txt)
            self.statusMessage.emit(tr("KI-Deutung in die Zwischenablage kopiert!"))

    def save_ai_as(self):
        if not self._ai_text.strip():
            return
        safe = re.sub(r'[\\/:*?"<>|]+', "_", self.chart["name"] if self.chart else "Horoskop").strip() or "Horoskop"
        fn, _ = QFileDialog.getSaveFileName(self, tr("Deutung als Text speichern"), f"{safe}_Deutung.md", "Markdown (*.md);;Text (*.txt)")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self._ai_text)
            self.statusMessage.emit(f"{tr('Gespeichert unter')} {fn}")

    # Verlauf: jede Deutung wird automatisch abgelegt
    def _reading_prefix(self):
        name = self.chart["name"] if self.chart else ""
        return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_") or "Horoskop"

    def _save_reading(self, text):
        try:
            os.makedirs(READINGS_DIR, exist_ok=True)
            module = getattr(self, "_ai_module", "gesamt")
            path = os.path.join(READINGS_DIR, f"{self._reading_prefix()}__{module}__{time.strftime('%Y%m%d-%H%M%S')}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            return
        self._refresh_history()

    def _refresh_history(self):
        self.combo_history.blockSignals(True)
        self.combo_history.clear()
        self.combo_history.addItem(tr("— gespeicherte Deutungen —"), None)
        try:
            prefix = self._reading_prefix() + "__"
            files = sorted([f for f in os.listdir(READINGS_DIR) if f.startswith(prefix)], reverse=True)
        except OSError:
            files = []
        for f in files[:50]:
            parts = f[:-3].split("__")
            label = f"{parts[2][:4]}-{parts[2][4:6]}-{parts[2][6:8]} {parts[2][9:11]}:{parts[2][11:13]} · {parts[1]}" if len(parts) == 3 else f
            self.combo_history.addItem(label, os.path.join(READINGS_DIR, f))
        self.combo_history.blockSignals(False)

    def _open_history(self, index):
        path = self.combo_history.itemData(index)
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._ai_text = f.read()
            self.text_ai.setMarkdown(self._ai_text)
