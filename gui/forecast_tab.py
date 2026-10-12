# -*- coding: utf-8 -*-
"""
Astrorust — Prognose-Panel: Zeitschieber (Transite), Progressionen/Solarbogen, Returns,
Transitsuche mit Zeitleiste, Himmelskalender (Ingresse, Stationen, Phasen, Finsternisse),
grafische Ephemeride (90°-Scheibe).
"""

import math
from datetime import datetime, timezone, timedelta

from PyQt6.QtCore import Qt, QDate, QTimer, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QCursor
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QSlider,
    QSpinBox, QDoubleSpinBox, QCheckBox, QScrollArea, QToolTip, QApplication, QGroupBox, QSplitter, QFrame, QTableWidget,
)

import styles
from i18n import tr
from widgets import AstroDateEdit, CityLineEdit, make_table, set_rows, esc

MAJOR = ["Conjunction", "Sextile", "Square", "Trine", "Opposition"]
ASPECT_CHOICES = [
    ("Conjunction", "☌ Konjunktion"), ("Sextile", "⚹ Sextil"), ("Square", "□ Quadrat"),
    ("Trine", "△ Trigon"), ("Opposition", "☍ Opposition"), ("Quincunx", "⚻ Quinkunx"),
    ("SemiSquare", "∠ Halbquadrat"), ("Sesquiquadrate", "⚼ Anderthalbquadrat"),
]
BODY_CHOICES = [
    ("Sun", "☉ Sonne"), ("Moon", "☽ Mond"), ("Mercury", "☿ Merkur"), ("Venus", "♀ Venus"), ("Mars", "♂ Mars"),
    ("Jupiter", "♃ Jupiter"), ("Saturn", "♄ Saturn"), ("Uranus", "♅ Uranus"), ("Neptune", "♆ Neptun"),
    ("Pluto", "♇ Pluto"), ("Chiron", "⚷ Chiron"),
]


def tp_from_qdate(d: QDate, hour=0, minute=0, tz=0.0):
    return {"year": d.year(), "month": d.month(), "day": d.day(), "hour": hour, "minute": minute, "timezone_offset": tz}


class WaitCursor:
    def __enter__(self):
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

    def __exit__(self, *a):
        QApplication.restoreOverrideCursor()


# ──────────────────────────────────────────────────────────────────────────
# Zeitleiste der Transite
# ──────────────────────────────────────────────────────────────────────────

class TransitTimeline(QWidget):
    LABEL_W = 170
    ROW_H = 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events = []
        self.start_jd = 0
        self.end_jd = 1
        self.setMouseTracking(True)
        self.setMinimumHeight(120)
        self._rects = []

    def set_events(self, events, start_jd, end_jd):
        self.events = sorted(events, key=lambda e: (e["exact_jds"][0] if e["exact_jds"] else e["enter_jd"]))
        self.start_jd, self.end_jd = start_jd, end_jd
        self.setFixedHeight(max(120, 34 + self.ROW_H * len(self.events)))
        self.update()

    def _x(self, jd):
        span = max(1e-9, self.end_jd - self.start_jd)
        return self.LABEL_W + (jd - self.start_jd) / span * (self.width() - self.LABEL_W - 10)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(styles.WINDOW))
        self._rects = []
        if not self.events:
            p.setPen(QColor(styles.TEXT_MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("Keine Transite im Zeitraum"))
            return

        # Monatsraster
        d0 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=self.start_jd - 2451545.0)
        d1 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=self.end_jd - 2451545.0)
        y, m = d0.year, d0.month
        p.setFont(QFont("sans-serif", 8))
        months = (d1.year - d0.year) * 12 + d1.month - d0.month
        step = 1 if months <= 14 else (3 if months <= 48 else 12)
        while True:
            first = datetime(y, m, 1, 12, tzinfo=timezone.utc)
            if first > d1:
                break
            jd = 2451545.0 + (first - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400.0
            if jd >= self.start_jd:
                x = self._x(jd)
                p.setPen(QPen(QColor(styles.BORDER_SOFT), 1))
                p.drawLine(QPointF(x, 18), QPointF(x, self.height()))
                p.setPen(QColor(styles.TEXT_MUTED))
                label = f"{first.year}" if m == 1 and step >= 12 else (f"{first.strftime('%b')} {first.year % 100:02d}" if m == 1 or step > 1 else first.strftime("%b"))
                p.drawText(QPointF(x + 2, 12), label)
            m += step
            while m > 12:
                m -= 12
                y += 1

        # heute
        now_jd = 2451545.0 + (datetime.now(timezone.utc) - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400.0
        if self.start_jd <= now_jd <= self.end_jd:
            p.setPen(QPen(QColor(styles.WARN_ORANGE), 1.5, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(self._x(now_jd), 16), QPointF(self._x(now_jd), self.height()))

        for i, e in enumerate(self.events):
            y0 = 22 + i * self.ROW_H
            p.setFont(QFont("serif", 9))
            p.setPen(QColor(styles.TEXT))
            p.drawText(QRectF(4, y0, self.LABEL_W - 8, self.ROW_H), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                       f"{e['transit_glyph']} {e['aspect_glyph']} {e['natal_glyph']}  {e['transit_body']}→{e['natal_point']}")
            x1, x2 = self._x(max(e["enter_jd"], self.start_jd)), self._x(min(e["leave_jd"], self.end_jd))
            col = QColor(e["color_hex"])
            col.setAlpha(150)
            rect = QRectF(x1, y0 + 3, max(3.0, x2 - x1), self.ROW_H - 7)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(col))
            p.drawRoundedRect(rect, 3, 3)
            self._rects.append((rect.adjusted(0, -3, 0, 3), e))
            p.setPen(QPen(QColor("#ffffff"), 2))
            for jd in e["exact_jds"]:
                x = self._x(jd)
                p.drawLine(QPointF(x, y0 + 2), QPointF(x, y0 + self.ROW_H - 3))

    def mouseMoveEvent(self, ev):
        for rect, e in self._rects:
            if rect.contains(ev.position()):
                exact = ", ".join(e["exact_labels"]) or tr("—")
                QToolTip.showText(self.mapToGlobal(ev.pos()), (
                    f"<b>{e['transit_glyph']} {e['transit_body']} {e['aspect_glyph']} {e['natal_glyph']} {e['natal_point']}</b><br>"
                    f"{tr('Beginn')}: {e['enter_label']}<br>{tr('Exakt')}: {exact}<br>{tr('Ende')}: {e['leave_label']}"), self)
                return
        QToolTip.hideText()


# ──────────────────────────────────────────────────────────────────────────
# Grafische Ephemeride
# ──────────────────────────────────────────────────────────────────────────

PLANET_COLORS = {
    "Sonne": "#eab308", "Mond": "#cbd5e1", "Merkur": "#a3e635", "Venus": "#f472b6", "Mars": "#ef4444",
    "Jupiter": "#fb923c", "Saturn": "#94a3b8", "Uranus": "#22d3ee", "Neptun": "#818cf8", "Pluto": "#a855f7",
    "Chiron": "#34d399",
}


class GraphicEphemerisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.setMinimumHeight(260)
        self.setMouseTracking(True)

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(styles.WINDOW))
        if not self.data:
            p.setPen(QColor(styles.TEXT_MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr("Zeitraum wählen und „Zeichnen“ drücken"))
            return
        l, t, r, b = 44, 14, 8, 24
        W, H = self.width() - l - r, self.height() - t - b
        times = self.data["times"]
        t0, t1 = times[0], times[-1]
        X = lambda jd: l + (jd - t0) / max(1e-9, t1 - t0) * W
        Y = lambda d: t + (1 - d / 90.0) * H
        p.setFont(QFont("sans-serif", 8))
        for deg in range(0, 91, 15):
            p.setPen(QPen(QColor(styles.BORDER_SOFT), 1))
            p.drawLine(QPointF(l, Y(deg)), QPointF(l + W, Y(deg)))
            p.setPen(QColor(styles.TEXT_MUTED))
            p.drawText(QRectF(2, Y(deg) - 8, l - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{deg}°")
        # Monate
        d0 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=t0 - 2451545.0)
        d1 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=t1 - 2451545.0)
        y, m = d0.year, d0.month
        months = (d1.year - d0.year) * 12 + d1.month - d0.month
        step = 1 if months <= 14 else (3 if months <= 48 else 12)
        while True:
            first = datetime(y, m, 1, 12, tzinfo=timezone.utc)
            if first > d1:
                break
            jd = 2451545.0 + (first - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400.0
            if jd >= t0:
                p.setPen(QPen(QColor(styles.BORDER_SOFT), 1))
                p.drawLine(QPointF(X(jd), t), QPointF(X(jd), t + H))
                p.setPen(QColor(styles.TEXT_MUTED))
                p.drawText(QPointF(X(jd) + 2, self.height() - 8),
                           f"{first.strftime('%b')} {first.year % 100:02d}" if (m == 1 or step > 1) else first.strftime("%b"))
            m += step
            while m > 12:
                m -= 12
                y += 1
        # Radixlinien
        for nl in self.data["natal_lines"]:
            p.setPen(QPen(QColor(styles.TEXT_DISABLED), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(l, Y(nl["dial"])), QPointF(l + W, Y(nl["dial"])))
            p.setFont(QFont("serif", 8))
            p.setPen(QColor(styles.TEXT_MUTED))
            p.drawText(QRectF(l + W - 26, Y(nl["dial"]) - 9, 26, 12), Qt.AlignmentFlag.AlignRight, nl["glyph"])
        # Planetenkurven (Sprung bei 90° → Linie unterbrechen)
        for s in self.data["series"]:
            col = QColor(PLANET_COLORS.get(s["body"], "#e2e8f0"))
            p.setPen(QPen(col, 1.6))
            prev = None
            for jd, d in zip(times, s["dial"]):
                pt = QPointF(X(jd), Y(d))
                if prev is not None and abs(d - prev[1]) < 45:
                    p.drawLine(prev[0], pt)
                prev = (pt, d)
            # Beschriftung am Ende
            p.setFont(QFont("serif", 9, QFont.Weight.Bold))
            p.setPen(col)
            p.drawText(QPointF(l + 4, Y(s["dial"][0]) - 2), s["glyph"])


# ──────────────────────────────────────────────────────────────────────────
# Panel
# ──────────────────────────────────────────────────────────────────────────

class ForecastPanel(QTabWidget):
    # kind ("transit"|"progression"|"return"), outer chart, cross aspects, label
    overlayChanged = pyqtSignal(str, dict, list, str)
    status = pyqtSignal(str)

    def __init__(self, backend, get_request, get_display_zone, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.get_request = get_request          # () -> natal request dict (with settings)
        self.get_display_zone = get_display_zone
        self.last_progression = None
        self.last_return = None
        self.last_transit = None
        self.transit_datetime = datetime.now(timezone.utc)
        self.transit_timer = QTimer(self)
        self.transit_timer.setInterval(250)
        self.transit_timer.timeout.connect(lambda: self.step_transit(86400))

        self.addTab(self._tab_slider(), tr("Zeitschieber"))
        self.addTab(self._tab_progression(), tr("Progression"))
        self.addTab(self._tab_return(), tr("Returns"))
        self.addTab(self._tab_search(), tr("Transitsuche"))
        self.addTab(self._tab_sky(), tr("Himmelskalender"))
        self.addTab(self._tab_ephemeris(), tr("Ephemeride"))

    def clear_results(self):
        self.transit_timer.stop()
        self.btn_play.setText(tr("▶ Animation starten"))
        self.last_progression = self.last_return = self.last_transit = None
        for table in self.findChildren(QTableWidget):
            table.setRowCount(0)
        self.timeline.set_events([], 0, 1)
        self.eph_widget.set_data(None)
        for label in (self.lbl_prog, self.lbl_search):
            label.clear()

    # ───────────── Zeitschieber ─────────────
    def _tab_slider(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)

        self.lbl_clock = QLabel(self.transit_datetime.strftime("%Y-%m-%d %H:%M UTC"))
        self.lbl_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_clock.setStyleSheet(
            f"font-family: monospace; font-size: 13px; font-weight: bold; color: {styles.ACCENT}; "
            f"background: {styles.SURFACE_SUNKEN}; padding: 6px; border-radius: 4px;")
        lay.addWidget(self.lbl_clock)

        row = QHBoxLayout()
        row.setSpacing(3)
        for label, delta in [("-1J", -31536000), ("-1M", -2592000), ("-1T", -86400), ("-1h", -3600), ("-10m", -600)]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, d=delta: self.step_transit(d))
            row.addWidget(b)
        lay.addLayout(row)

        row = QHBoxLayout()
        self.btn_play = QPushButton(tr("▶ Animation starten"))
        self.btn_play.setObjectName("btn_play")
        self.btn_play.clicked.connect(self.toggle_play)
        row.addWidget(self.btn_play)
        b = QPushButton(tr("Jetzt"))
        b.clicked.connect(self.reset_now)
        row.addWidget(b)
        lay.addLayout(row)

        row = QHBoxLayout()
        row.setSpacing(3)
        for label, delta in [("+10m", 600), ("+1h", 3600), ("+1T", 86400), ("+1M", 2592000), ("+1J", 31536000)]:
            b = QPushButton(label)
            b.clicked.connect(lambda _, d=delta: self.step_transit(d))
            row.addWidget(b)
        lay.addLayout(row)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-30, 30)
        self.slider.valueChanged.connect(self._on_slider)
        lay.addWidget(QLabel(tr("Regler: ±30 Jahre um heute")))
        lay.addWidget(self.slider)

        self.table_transits = make_table(["Transit", "Aspekt", "Radix", "Orbis", ""], stretch_col=1)
        lay.addWidget(self.table_transits, 1)
        return w

    def toggle_play(self):
        if self.transit_timer.isActive():
            self.transit_timer.stop()
            self.btn_play.setText(tr("▶ Animation starten"))
        else:
            self.transit_timer.start()
            self.btn_play.setText(tr("⏸ Pause"))

    def reset_now(self):
        self.transit_datetime = datetime.now(timezone.utc)
        self.update_transits()

    def step_transit(self, seconds):
        self.transit_datetime = datetime.fromtimestamp(self.transit_datetime.timestamp() + seconds, timezone.utc)
        self.update_transits()

    def _on_slider(self, val):
        now = datetime.now(timezone.utc)
        self.transit_datetime = datetime.fromtimestamp(now.timestamp() + val * 365.25 * 86400, timezone.utc)
        self.update_transits()

    def update_transits(self, activate=True):
        dt = self.transit_datetime
        self.lbl_clock.setText(dt.strftime("%Y-%m-%d %H:%M UTC"))
        try:
            req = {
                "natal": self.get_request(),
                "transit_year": dt.year, "transit_month": dt.month, "transit_day": dt.day,
                "transit_hour": dt.hour, "transit_minute": dt.minute, "transit_timezone_offset": 0.0,
            }
            res = self.backend.call("transit", req)
        except Exception as e:
            self.status.emit(f"{tr('Transitberechnung fehlgeschlagen')}: {e}")
            return
        asp = res.get("transit_aspects", [])
        self.last_transit = res
        rows = [[f"{a['transit_glyph']} {a['transit_name']}", f"{a['aspect_glyph']} {a['aspect_name']}",
                 f"{a['natal_glyph']} {a['natal_name']}", a["formatted_orb"], "→" if a.get("is_applying") else "←"] for a in asp]
        colors = {(i, 1): a.get("color_hex", styles.ACCENT) for i, a in enumerate(asp)}
        set_rows(self.table_transits, rows, colors)
        if activate:
            self.overlayChanged.emit("transit", res["transit_chart"], asp, dt.strftime("%Y-%m-%d %H:%M UTC"))

    # ───────────── Progression ─────────────
    def _tab_progression(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        row = QHBoxLayout()
        self.combo_prog = QComboBox()
        self.combo_prog.addItem(tr("Sekundärprogression (Tag = Jahr)"), "secondary")
        self.combo_prog.addItem(tr("Solarbogen-Direktion"), "solar_arc")
        self.combo_prog.addItem(tr("Tertiärprogression (Tag = Mondumlauf)"), "tertiary")
        self.combo_prog.addItem(tr("Minorprogression (Mondumlauf = Jahr)"), "minor")
        row.addWidget(self.combo_prog, 1)
        row.addWidget(QLabel(tr("für:")))
        self.prog_date = AstroDateEdit(QDate.currentDate())
        row.addWidget(self.prog_date)
        self.prog_orb = QDoubleSpinBox()
        self.prog_orb.setRange(0.1, 3.0)
        self.prog_orb.setSingleStep(0.1)
        self.prog_orb.setValue(1.0)
        self.prog_orb.setSuffix(" °")
        self.prog_orb.setToolTip(tr("Orbis für Aspekte zum Radix"))
        row.addWidget(self.prog_orb)
        b = QPushButton(tr("Berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run_progression)
        row.addWidget(b)
        lay.addLayout(row)
        self.lbl_prog = QLabel("")
        self.lbl_prog.setWordWrap(True)
        self.lbl_prog.setStyleSheet(f"background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px; font-size: 11px;")
        lay.addWidget(self.lbl_prog)
        self.table_prog = make_table(["Progr.", "Aspekt", "Radix", "Orbis", ""], stretch_col=1)
        lay.addWidget(self.table_prog, 2)
        self.table_prog_pos = make_table(["Pt", "Punkt", "Position", "Haus"], stretch_col=2)
        lay.addWidget(self.table_prog_pos, 2)
        return w

    def run_progression(self):
        if not self.prog_date.is_valid_input():
            self.status.emit(tr("Ungültiges Datum"))
            return
        try:
            with WaitCursor():
                res = self.backend.call("progression", {
                    "natal": self.get_request(),
                    "target": tp_from_qdate(self.prog_date.date(), 12),
                    "kind": self.combo_prog.currentData(),
                    "orb": self.prog_orb.value(),
                })
        except Exception as e:
            self.lbl_prog.setText(f"<span style='color:{styles.STOP_RED}'>{esc(e)}</span>")
            return
        self.last_progression = res
        pc = res["progressed_chart"]
        self.lbl_prog.setText(
            f"<b>{esc(res['kind_label'])}</b> — {tr('Alter')}: {res['age_years']:.2f} {tr('Jahre')} · "
            f"{tr('Solarbogen')}: {res['solar_arc']:.2f}°"
            + (f" · {tr('Progressive Mondphase')}: {esc(res['moon_phase'])}" if res.get("moon_phase") else ""))
        asp = res["aspects_to_natal"]
        set_rows(self.table_prog,
                 [[f"{a['transit_glyph']} {a['transit_name']}", f"{a['aspect_glyph']} {a['aspect_name']}",
                   f"{a['natal_glyph']} {a['natal_name']}", a["formatted_orb"], "→" if a.get("is_applying") else "←"] for a in asp],
                 {(i, 1): a["color_hex"] for i, a in enumerate(asp)})
        set_rows(self.table_prog_pos, [[p["glyph"], p["name"], f"{p['formatted_deg']} {p['sign_glyph']}", f"{p['house']}."] for p in pc["planets"]])
        self.overlayChanged.emit("progression", pc, asp, res["kind_label"])

    # ───────────── Returns ─────────────
    def _tab_return(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        row = QHBoxLayout()
        self.combo_ret = QComboBox()
        for key, name in [("Sun", tr("Solar-Return (Sonne)")), ("Moon", tr("Lunar-Return (Mond)")), ("Mercury", tr("Merkur-Return")),
                          ("Venus", tr("Venus-Return")), ("Mars", tr("Mars-Return")), ("Jupiter", tr("Jupiter-Return")),
                          ("Saturn", tr("Saturn-Return")), ("Chiron", tr("Chiron-Return")), ("Uranus", tr("Uranus-Opposition/Return")),
                          ]:
            self.combo_ret.addItem(name, key)
        row.addWidget(self.combo_ret, 1)
        row.addWidget(QLabel(tr("ab:")))
        self.ret_date = AstroDateEdit(QDate.currentDate())
        row.addWidget(self.ret_date)
        self.ret_count = QSpinBox()
        self.ret_count.setRange(1, 24)
        self.ret_count.setValue(1)
        self.ret_count.setToolTip(tr("Anzahl aufeinanderfolgender Returns (das Horoskop gibt es für den ersten)"))
        row.addWidget(self.ret_count)
        lay.addLayout(row)

        row = QHBoxLayout()
        self.chk_reloc = QCheckBox(tr("Anderer Ort (Relokation):"))
        row.addWidget(self.chk_reloc)
        self.reloc_city = CityLineEdit(self.backend)
        self.reloc_city.setEnabled(False)
        self.reloc_data = None
        self.reloc_city.cityChosen.connect(self._on_reloc_city)
        self.chk_reloc.toggled.connect(self.reloc_city.setEnabled)
        row.addWidget(self.reloc_city, 1)
        b = QPushButton(tr("Berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run_return)
        row.addWidget(b)
        lay.addLayout(row)

        self.table_ret_times = make_table(["Nr.", "Zeitpunkt (Ortszeit)"], stretch_col=1)
        self.table_ret_times.setMaximumHeight(130)
        lay.addWidget(self.table_ret_times)
        self.table_ret = make_table(["Return", "Aspekt", "Radix", "Orbis", ""], stretch_col=1)
        lay.addWidget(self.table_ret, 2)
        self.table_ret_pos = make_table(["Pt", "Punkt", "Position", "Haus"], stretch_col=2)
        lay.addWidget(self.table_ret_pos, 2)
        return w

    def _on_reloc_city(self, c):
        self.reloc_city.setText(f"{c['name']}, {c['country']}")
        self.reloc_data = c

    def run_return(self):
        if not self.ret_date.is_valid_input():
            self.status.emit(tr("Ungültiges Datum"))
            return
        try:
            req = {
                "natal": self.get_request(),
                "body": self.combo_ret.currentData(),
                "start": tp_from_qdate(self.ret_date.date()),
                "count": self.ret_count.value(),
                "display_timezone": self.get_display_zone(),
            }
            if self.chk_reloc.isChecked() and self.reloc_data:
                req.update({"latitude": self.reloc_data["latitude"], "longitude": self.reloc_data["longitude"],
                            "location_name": f"{self.reloc_data['name']}, {self.reloc_data['country']}",
                            "display_timezone": self.reloc_data.get("timezone") or req["display_timezone"]})
            with WaitCursor():
                res = self.backend.call("return", req)
        except Exception as e:
            self.status.emit(str(e))
            self.table_ret_times.setRowCount(0)
            set_rows(self.table_ret_times, [["!", str(e)]])
            return
        self.last_return = res
        set_rows(self.table_ret_times, [[i + 1, r["label"]] for i, r in enumerate(res["returns"])])
        asp = res["aspects_to_natal"]
        set_rows(self.table_ret,
                 [[f"{a['transit_glyph']} {a['transit_name']}", f"{a['aspect_glyph']} {a['aspect_name']}",
                   f"{a['natal_glyph']} {a['natal_name']}", a["formatted_orb"], "→" if a.get("is_applying") else "←"] for a in asp],
                 {(i, 1): a["color_hex"] for i, a in enumerate(asp)})
        ch = res["chart"]
        set_rows(self.table_ret_pos, [[p["glyph"], p["name"], f"{p['formatted_deg']} {p['sign_glyph']}", f"{p['house']}."] for p in ch["planets"]])
        self.overlayChanged.emit("return", ch, asp, f"{ch['name']} ({res['returns'][0]['label']})")

    # ───────────── Transitsuche ─────────────
    def _range_row(self, default_days):
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("von")))
        a = AstroDateEdit(QDate.currentDate())
        row.addWidget(a)
        row.addWidget(QLabel(tr("bis")))
        b = AstroDateEdit(QDate.currentDate().addDays(default_days))
        row.addWidget(b)
        return row, a, b

    def _tab_search(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        row, self.search_from, self.search_to = self._range_row(365)
        self.search_orb = QDoubleSpinBox()
        self.search_orb.setRange(0.2, 3.0)
        self.search_orb.setSingleStep(0.2)
        self.search_orb.setValue(1.0)
        self.search_orb.setSuffix(" °")
        self.search_orb.setToolTip(tr("Orbis, ab dem ein Transit „beginnt“ und „endet“"))
        row.addWidget(self.search_orb)
        b = QPushButton(tr("Suchen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run_search)
        row.addWidget(b)
        lay.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Transit durch:")))
        self.search_bodies = {}
        for key, label in BODY_CHOICES:
            c = QCheckBox(label.split(" ")[0])
            c.setToolTip(label[2:])
            c.setChecked(key not in ("Moon", "Chiron"))
            row.addWidget(c)
            self.search_bodies[key] = c
        row.addStretch()
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Aspekte:")))
        self.search_aspects = {}
        for key, label in ASPECT_CHOICES:
            c = QCheckBox(label.split(" ")[0])
            c.setToolTip(label)
            c.setChecked(key in MAJOR)
            row.addWidget(c)
            self.search_aspects[key] = c
        row.addStretch()
        lay.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table_search = make_table(["Transit", "Aspekt", "Radix", "Beginn", "Exakt", "Ende"], stretch_col=4)
        splitter.addWidget(self.table_search)
        self.timeline = TransitTimeline()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.timeline)
        splitter.addWidget(scroll)
        splitter.setSizes([260, 260])
        lay.addWidget(splitter, 1)
        self.lbl_search = QLabel("")
        self.lbl_search.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(self.lbl_search)
        return w

    def run_search(self):
        if not (self.search_from.is_valid_input() and self.search_to.is_valid_input()):
            self.status.emit(tr("Ungültiges Datum"))
            return
        bodies = [k for k, c in self.search_bodies.items() if c.isChecked()]
        aspects = [k for k, c in self.search_aspects.items() if c.isChecked()]
        try:
            with WaitCursor():
                res = self.backend.call("transit_search", {
                    "natal": self.get_request(),
                    "start": tp_from_qdate(self.search_from.date()), "end": tp_from_qdate(self.search_to.date()),
                    "bodies": bodies, "aspects": aspects, "orb": self.search_orb.value(),
                    "display_timezone": self.get_display_zone(),
                })
        except Exception as e:
            self.lbl_search.setText(f"<span style='color:{styles.STOP_RED}'>{esc(e)}</span>")
            return
        ev = res["events"]
        rows = [[f"{e['transit_glyph']} {e['transit_body']}", f"{e['aspect_glyph']} {e['aspect_name']}",
                 f"{e['natal_glyph']} {e['natal_point']}",
                 ("◂ " if e["starts_before_range"] else "") + e["enter_label"][:16],
                 " · ".join(x[:16] for x in e["exact_labels"]) or "—",
                 e["leave_label"][:16] + (" ▸" if e["ends_after_range"] else "")] for e in ev]
        set_rows(self.table_search, rows, {(i, 1): e["color_hex"] for i, e in enumerate(ev)})
        self.timeline.set_events(ev, res["start_jd"], res["end_jd"])
        self.lbl_search.setText(f"{len(ev)} {tr('Transite')} · {tr('Weiß = exakt, Balken = Orbis')} ±{self.search_orb.value():.1f}°")

    # ───────────── Himmelskalender ─────────────
    def _tab_sky(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        row, self.sky_from, self.sky_to = self._range_row(120)
        b = QPushButton(tr("Anzeigen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run_sky)
        row.addWidget(b)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.sky_kinds = {}
        for key, label in [("ingress", tr("Ingresse")), ("station", tr("Stationen")), ("phase", tr("Mondphasen")), ("eclipse", tr("Finsternisse"))]:
            c = QCheckBox(label)
            c.setChecked(True)
            row.addWidget(c)
            self.sky_kinds[key] = c
        self.chk_sky_natal = QCheckBox(tr("Kontakte zum Radix zeigen"))
        self.chk_sky_natal.setChecked(True)
        row.addWidget(self.chk_sky_natal)
        row.addStretch()
        lay.addLayout(row)
        self.table_sky = make_table(["Zeitpunkt", "Ereignis", "Position", "Kontakte zum Radix"], stretch_col=3)
        lay.addWidget(self.table_sky, 1)
        return w

    def run_sky(self):
        if not (self.sky_from.is_valid_input() and self.sky_to.is_valid_input()):
            self.status.emit(tr("Ungültiges Datum"))
            return
        try:
            req = {
                "start": tp_from_qdate(self.sky_from.date()), "end": tp_from_qdate(self.sky_to.date()),
                "kinds": [k for k, c in self.sky_kinds.items() if c.isChecked()],
                "display_timezone": self.get_display_zone(),
            }
            natal = self.get_request()
            req["settings"] = natal.get("settings")
            if self.chk_sky_natal.isChecked():
                req["natal"] = natal
            with WaitCursor():
                ev = self.backend.call("sky_events", req)
        except Exception as e:
            set_rows(self.table_sky, [["!", str(e), "", ""]])
            return
        colors = {}
        rows = []
        for i, e in enumerate(ev):
            rows.append([e["label"], e["title"], e["formatted"], " · ".join(e["natal_contacts"])])
            if e["natal_contacts"]:
                colors[(i, 3)] = styles.WARN_ORANGE
        set_rows(self.table_sky, rows, colors)

    # ───────────── Ephemeride ─────────────
    def _tab_ephemeris(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(6, 6, 6, 6)
        row, self.eph_from, self.eph_to = self._range_row(365)
        b = QPushButton(tr("Zeichnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run_ephemeris)
        row.addWidget(b)
        lay.addLayout(row)
        info = QLabel(tr("Grafische Ephemeride auf der 90°-Scheibe: Planetenbahnen (Länge mod 90°) gegen die Zeit; gestrichelt die Radixpunkte – Schnittpunkte sind Hart-Aspekte und Halbsummen-Auslösungen."))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(info)
        self.eph_widget = GraphicEphemerisWidget()
        lay.addWidget(self.eph_widget, 1)
        return w

    def run_ephemeris(self):
        if not (self.eph_from.is_valid_input() and self.eph_to.is_valid_input()):
            self.status.emit(tr("Ungültiges Datum"))
            return
        days = self.eph_from.date().daysTo(self.eph_to.date())
        try:
            with WaitCursor():
                data = self.backend.call("graphic_ephemeris", {
                    "natal": self.get_request(),
                    "start": tp_from_qdate(self.eph_from.date()), "end": tp_from_qdate(self.eph_to.date()),
                    "step_days": 1.0 if days <= 800 else 5.0,
                })
        except Exception as e:
            self.status.emit(str(e))
            return
        self.eph_widget.set_data(data)
