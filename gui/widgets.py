# -*- coding: utf-8 -*-
"""
Astrorust — wiederverwendbare Widgets: Datumsfeld, Ortssuche, Personen-Eingabe, Tabellen-Helfer.
"""

import html
import re

from PyQt6.QtCore import Qt, QDate, QTime, QCalendar, QStringListModel, pyqtSignal
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWidgets import (
    QLineEdit, QCompleter, QDialog, QVBoxLayout, QCalendarWidget, QWidget, QGridLayout, QLabel,
    QTimeEdit, QDoubleSpinBox, QComboBox, QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QHBoxLayout, QCheckBox,
)

import styles
from i18n import tr


def tab_text(text: str) -> str:
    """Tab-/Menütexte: ein einzelnes & würde sonst als Tastenkürzel verschluckt."""
    return text.replace("&", "&&")


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


# ──────────────────────────────────────────────────────────────────────────
# Datum
# ──────────────────────────────────────────────────────────────────────────

class CivilDate:
    """A civil date with the calendar used by the calculation engine."""
    def __init__(self, year, month, day):
        self.calendar = QCalendar(QCalendar.System.Julian) if (year, month, day) < (1582, 10, 15) else QCalendar()
        self.value = QDate(year, month, day, self.calendar)

    def year(self):
        return self.value.year(self.calendar)

    def month(self):
        return self.value.month(self.calendar)

    def day(self):
        return self.value.day(self.calendar)

    def isValid(self):
        return self.value.isValid()

    def toString(self, fmt):
        return self.value.toString(fmt, self.calendar)

    def daysTo(self, other):
        return self.value.daysTo(other.value if isinstance(other, CivilDate) else other)


class AstroDateEdit(QLineEdit):
    """
    Flexibles Datumseingabefeld: '1985-05-15', '15.05.1985', '1985/05/15'.
    Ungültige Eingaben werden rot markiert und von `is_valid_input()` gemeldet.
    Daten vor dem 15.10.1582 werden von der Rechenbibliothek als Julianisch gelesen.
    """

    valueChanged = pyqtSignal()

    def __init__(self, default_date=None, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(tr("JJJJ-MM-TT oder TT.MM.JJJJ"))
        d = default_date or QDate.currentDate()
        self._current_date = CivilDate(d.year(), d.month(), d.day())
        self.setText(self._current_date.toString("yyyy-MM-dd"))

        cal_icon = QIcon.fromTheme("view-calendar", QIcon.fromTheme("x-office-calendar"))
        if cal_icon.isNull():
            cal_icon = self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogStart)
        self.cal_action = self.addAction(cal_icon, QLineEdit.ActionPosition.TrailingPosition)
        self.cal_action.setToolTip(tr("Kalender öffnen"))
        self.cal_action.triggered.connect(self._open_calendar)
        self.editingFinished.connect(self._on_editing_finished)

    def setDate(self, qdate: QDate):
        if qdate and qdate.isValid():
            self._current_date = CivilDate(qdate.year(), qdate.month(), qdate.day())
            self.setText(self._current_date.toString("yyyy-MM-dd"))
            self.setStyleSheet("")
            self.setToolTip("")
            self.valueChanged.emit()

    def date(self) -> QDate:
        if not self._parse_text():
            raise ValueError(tr("Ungültiges Datum – erlaubt: JJJJ-MM-TT oder TT.MM.JJJJ"))
        return self._current_date

    def is_valid_input(self) -> bool:
        return self._parse_text()

    def _parse_text(self) -> bool:
        text = self.text().strip()
        if not text:
            return False
        m = re.match(r"^(\d{3,4})[-/.](\d{1,2})[-/.](\d{1,2})$", text)
        if m:
            qd = CivilDate(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if qd.isValid():
                self._current_date = qd
                return True
            return False
        m = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{3,4})$", text)
        if m:
            qd = CivilDate(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            if qd.isValid():
                self._current_date = qd
                return True
        return False

    def _on_editing_finished(self):
        if self._parse_text():
            self.setText(self._current_date.toString("yyyy-MM-dd"))
            self.setStyleSheet("")
            self.setToolTip("")
            self.valueChanged.emit()
        else:
            self.setStyleSheet(f"border: 1px solid {styles.STOP_RED};")
            self.setToolTip(tr("Ungültiges Datum – erlaubt: JJJJ-MM-TT oder TT.MM.JJJJ"))

    def _open_calendar(self):
        self._parse_text()
        dlg = QDialog(self, Qt.WindowType.Popup)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(6, 6, 6, 6)
        cal = QCalendarWidget(dlg)
        cal.setCalendar(self._current_date.calendar)
        cal.setGridVisible(True)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        if self._current_date.isValid():
            cal.setSelectedDate(self._current_date.value)
        def choose(d):
            calendar = cal.calendar()
            self.setDate(CivilDate(d.year(calendar), d.month(calendar), d.day(calendar)))
            dlg.accept()
        cal.activated.connect(choose)
        cal.clicked.connect(choose)
        lay.addWidget(cal)
        dlg.move(self.mapToGlobal(self.rect().bottomLeft()))
        dlg.exec()


# ──────────────────────────────────────────────────────────────────────────
# Ortssuche
# ──────────────────────────────────────────────────────────────────────────

class CityLineEdit(QLineEdit):
    """Ortsfeld mit Vervollständigung aus dem Atlas der Rust-Bibliothek."""

    cityChosen = pyqtSignal(dict)

    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._entries: dict[str, dict] = {}
        self._model = QStringListModel(self)
        self._completer = QCompleter(self._model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.setCompleter(self._completer)
        self.setPlaceholderText(tr("Ort suchen (Name, Land)…"))
        self.textEdited.connect(self._on_text_edited)
        self._completer.activated[str].connect(self._on_activated)

    def _label(self, c: dict) -> str:
        return f"{c['name']}, {c['country']}"

    def _on_text_edited(self, text: str):
        if len(text.strip()) < 2:
            return
        try:
            results = self._backend.search_cities(text)[:15]
        except Exception:
            return
        self._entries = {self._label(c): c for c in results}
        self._model.setStringList(list(self._entries.keys()))

    def _on_activated(self, text: str):
        entry = self._entries.get(text)
        if entry:
            self.cityChosen.emit(entry)


# ──────────────────────────────────────────────────────────────────────────
# Personen-Eingabe (Geburtsdaten + Zeitzone)
# ──────────────────────────────────────────────────────────────────────────

def compact_combo(combo: QComboBox, chars: int = 10) -> QComboBox:
    """Verhindert, dass lange Einträge das Eingabepanel verbreitern."""
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(chars)
    return combo


class PersonInput(QGroupBox):
    """Geburtsdaten einer Person; liefert eine Rust-kompatible Anfrage."""

    changed = pyqtSignal()

    HOUSE_SYSTEMS = ["Placidus", "Koch", "Regiomontanus", "Campanus", "WholeSign", "Equal", "Topocentric", "Porphyry"]

    def __init__(self, title, backend, defaults: dict, with_houses=True, parent=None):
        super().__init__(title, parent)
        self.backend = backend
        self._zones_loaded = False
        self._tz_info = None

        g = QGridLayout(self)
        g.setSpacing(6)

        g.setColumnStretch(1, 1)
        g.addWidget(QLabel(tr("Name:")), 0, 0)
        self.edit_name = QLineEdit(defaults.get("name", ""))
        g.addWidget(self.edit_name, 0, 1, 1, 2)

        g.addWidget(QLabel(tr("Datum:")), 1, 0)
        self.edit_date = AstroDateEdit(QDate(defaults.get("year", 2000), defaults.get("month", 1), defaults.get("day", 1)))
        g.addWidget(self.edit_date, 1, 1)
        self.edit_time = QTimeEdit()
        self.edit_time.setDisplayFormat("HH:mm")
        self.edit_time.setTime(QTime(defaults.get("hour", 12), defaults.get("minute", 0)))
        self.edit_time.setFixedWidth(78)
        g.addWidget(self.edit_time, 1, 2)

        g.addWidget(QLabel(tr("Ort:")), 2, 0)
        self.edit_city = CityLineEdit(backend)
        self.edit_city.setText(defaults.get("location_name", ""))
        g.addWidget(self.edit_city, 2, 1, 1, 2)

        g.addWidget(QLabel(tr("Breite (°):")), 3, 0)
        self.spin_lat = QDoubleSpinBox()
        self.spin_lat.setRange(-90.0, 90.0)
        self.spin_lat.setDecimals(4)
        self.spin_lat.setValue(defaults.get("latitude", 52.52))
        g.addWidget(self.spin_lat, 3, 1, 1, 2)
        g.addWidget(QLabel(tr("Länge (°):")), 4, 0)
        self.spin_lon = QDoubleSpinBox()
        self.spin_lon.setRange(-180.0, 180.0)
        self.spin_lon.setDecimals(4)
        self.spin_lon.setValue(defaults.get("longitude", 13.405))
        g.addWidget(self.spin_lon, 4, 1, 1, 2)

        g.addWidget(QLabel(tr("Zeitzone:")), 5, 0)
        self.combo_zone = compact_combo(QComboBox())
        self.combo_zone.setEditable(True)
        self.combo_zone.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.combo_zone.setToolTip(tr("IANA-Zone (z. B. Europe/Berlin): Sommerzeit und historische Zeiten werden automatisch bestimmt"))
        self.combo_zone.addItem(tr("— manueller UTC-Offset —"), "")
        g.addWidget(self.combo_zone, 5, 1)
        self.btn_zone = QPushButton("🌍")
        self.btn_zone.setFixedWidth(34)
        self.btn_zone.setToolTip(tr("Zeitzone zu Breite/Länge vorschlagen"))
        self.btn_zone.clicked.connect(self._suggest_zone)
        g.addWidget(self.btn_zone, 5, 2)

        g.addWidget(QLabel(tr("UTC-Offset (h):")), 6, 0)
        self.spin_tz = QDoubleSpinBox()
        self.spin_tz.setRange(-14.0, 14.0)
        self.spin_tz.setDecimals(2)
        self.spin_tz.setSingleStep(0.25)
        self.spin_tz.setValue(defaults.get("timezone_offset", 1.0))
        g.addWidget(self.spin_tz, 6, 1, 1, 2)

        self.lbl_tz = QLabel("")
        self.lbl_tz.setWordWrap(True)
        self.lbl_tz.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
        g.addWidget(self.lbl_tz, 7, 0, 1, 3)

        self.combo_houses = None
        if with_houses:
            g.addWidget(QLabel(tr("Häusersystem:")), 8, 0)
            self.combo_houses = compact_combo(QComboBox())
            self.combo_houses.addItems(self.HOUSE_SYSTEMS)
            g.addWidget(self.combo_houses, 8, 1, 1, 2)

        # Signale
        self.edit_city.cityChosen.connect(self._on_city_chosen)
        self.edit_date.valueChanged.connect(self._refresh_tz)
        self.edit_time.timeChanged.connect(self._on_time_changed)
        self.spin_lon.valueChanged.connect(self._refresh_tz)
        self.spin_tz.valueChanged.connect(self._on_offset_changed)
        self.combo_zone.currentIndexChanged.connect(self._on_zone_changed)
        self.combo_zone.lineEdit().editingFinished.connect(self._on_zone_text_edited)

        self.set_zone(defaults.get("timezone") or "")
        self._on_zone_changed()

    # ── Zonen laden (verzögert, damit der Start schnell bleibt) ──
    def _ensure_zones(self):
        if self._zones_loaded:
            return
        self._zones_loaded = True
        try:
            zones = self.backend.call("zones")
        except Exception:
            zones = []
        current = self.zone()
        self.combo_zone.blockSignals(True)
        for z in zones:
            if self.combo_zone.findData(z) < 0:
                self.combo_zone.addItem(z, z)
        self.combo_zone.blockSignals(False)
        self.set_zone(current)

    def showEvent(self, event):
        super().showEvent(event)
        self._ensure_zones()

    # ── Zone ──
    def zone(self) -> str:
        text = self.combo_zone.currentText().strip()
        data = self.combo_zone.currentData()
        if data and text == self.combo_zone.itemText(self.combo_zone.currentIndex()):
            return data
        if text and not text.startswith("—") and "/" in text:
            return text
        return ""

    def set_zone(self, zone: str):
        self.combo_zone.blockSignals(True)
        if not zone:
            self.combo_zone.setCurrentIndex(0)
        else:
            idx = self.combo_zone.findData(zone)
            if idx < 0:
                self.combo_zone.addItem(zone, zone)
                idx = self.combo_zone.findData(zone)
            self.combo_zone.setCurrentIndex(idx)
        self.combo_zone.blockSignals(False)
        self._on_zone_changed()

    def _on_zone_text_edited(self):
        text = self.combo_zone.currentText().strip()
        idx = self.combo_zone.findText(text)
        if idx >= 0:
            self.combo_zone.setCurrentIndex(idx)
        elif "/" in text:
            self.set_zone(text)

    def _on_zone_changed(self, *_):
        manual = not self.zone()
        self.spin_tz.setEnabled(manual)
        self._refresh_tz()

    def _on_offset_changed(self, *_):
        if not self.zone():
            self._refresh_tz()

    def _on_time_changed(self, *_):
        self._second = 0
        self._refresh_tz()

    def _suggest_zone(self):
        try:
            c = self.backend.call("atlas_nearest", {"latitude": self.spin_lat.value(), "longitude": self.spin_lon.value()})
        except Exception:
            return
        self._ensure_zones()
        self.set_zone(c.get("timezone", ""))

    def _on_city_chosen(self, c: dict):
        self.edit_city.setText(f"{c['name']}, {c['country']}")
        self.spin_lat.setValue(c["latitude"])
        self.spin_lon.setValue(c["longitude"])
        self._ensure_zones()
        self.set_zone(c.get("timezone", ""))

    def _refresh_tz(self, *_):
        zone = self.zone()
        if not zone:
            off = self.spin_tz.value()
            sign = "+" if off >= 0 else "−"
            self.lbl_tz.setText(f"{tr('Manueller Offset')}: UTC{sign}{abs(off):.2f} h")
            self.lbl_tz.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED};")
            self._tz_info = None
            self.changed.emit()
            return
        if not self.edit_date.is_valid_input():
            return
        d = self.edit_date.date()
        t = self.edit_time.time()
        try:
            info = self.backend.call("resolve_timezone", {
                "zone": zone, "year": d.year(), "month": d.month(), "day": d.day(),
                "hour": t.hour(), "minute": t.minute(), "longitude": self.spin_lon.value(),
            })
        except Exception as e:
            self.lbl_tz.setText(str(e))
            self.lbl_tz.setStyleSheet(f"font-size: 11px; color: {styles.STOP_RED};")
            self._tz_info = None
            return
        self._tz_info = info
        self.lbl_tz.setText(info.get("note", ""))
        color = styles.WARN_ORANGE if info.get("ambiguity") else styles.TEXT_MUTED
        self.lbl_tz.setStyleSheet(f"font-size: 11px; color: {color};")
        self.changed.emit()

    @property
    def tz_info(self):
        return self._tz_info

    # ── Daten ──
    def is_valid(self) -> bool:
        return self.edit_date.is_valid_input()

    def request(self, settings: dict | None, house_system: str | None = None) -> dict:
        d = self.edit_date.date()
        t = self.edit_time.time()
        zone = self.zone()
        req = {
            "name": self.edit_name.text().strip() or tr("Unbenannt"),
            "year": d.year(), "month": d.month(), "day": d.day(),
            "hour": t.hour(), "minute": t.minute(), "second": getattr(self, "_second", 0),
            "timezone_offset": self.spin_tz.value(),
            "timezone": zone or None,
            "latitude": self.spin_lat.value(),
            "longitude": self.spin_lon.value(),
            "location_name": self.edit_city.text().strip(),
            "house_system": house_system or (self.combo_houses.currentText() if self.combo_houses else "Placidus"),
        }
        if settings is not None:
            req["settings"] = settings
        return req

    def profile(self) -> dict:
        """Speicherformat (ohne Berechnungseinstellungen)."""
        req = self.request(None)
        req.pop("settings", None)
        return req

    def set_profile(self, p: dict):
        self.blockSignals(True)
        self.edit_name.setText(p.get("name", ""))
        self.edit_date.setDate(CivilDate(p.get("year", 2000), p.get("month", 1), p.get("day", 1)))
        self.edit_time.setTime(QTime(p.get("hour", 12), p.get("minute", 0)))
        self._second = p.get("second", 0)
        self.edit_city.setText(p.get("location_name", "") or "")
        self.spin_lat.setValue(p.get("latitude", 52.52))
        self.spin_lon.setValue(p.get("longitude", 13.405))
        self.spin_tz.setValue(p.get("timezone_offset", 1.0))
        self._ensure_zones()
        self.set_zone(p.get("timezone") or "")
        if self.combo_houses is not None:
            hs = p.get("house_system", "Placidus")
            i = self.combo_houses.findText(hs)
            if i >= 0:
                self.combo_houses.setCurrentIndex(i)
        self.blockSignals(False)
        self._refresh_tz()


# ──────────────────────────────────────────────────────────────────────────
# Tabellen
# ──────────────────────────────────────────────────────────────────────────

def make_table(headers, stretch_col=None, selectable=True) -> QTableWidget:
    t = QTableWidget()
    t.setColumnCount(len(headers))
    t.setHorizontalHeaderLabels([tr(h) for h in headers])
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(False)
    t.verticalHeader().setVisible(False)
    t.setWordWrap(False)
    if not selectable:
        t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    hh = t.horizontalHeader()
    hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch_col is not None:
        hh.setSectionResizeMode(stretch_col, QHeaderView.ResizeMode.Stretch)
    return t


def set_rows(table: QTableWidget, rows, colors=None):
    """rows: Liste von Listen; colors: optional {(row, col): '#hex'}."""
    table.setSortingEnabled(False)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem("" if value is None else tr(str(value)))
            if colors and (r, c) in colors:
                item.setForeground(QColor(colors[(r, c)]))
            table.setItem(r, c, item)
    table.resizeRowsToContents()
