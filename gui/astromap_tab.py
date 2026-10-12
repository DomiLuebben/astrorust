# -*- coding: utf-8 -*-
"""
Astrorust — Astrokartografie: Planetenlinien auf der Weltkarte und Orte nahe an Linien.

Küstenlinien: Ist `coastlines.geojson` im Programmordner oder in ~/.local/share/astrorust/ vorhanden
(z. B. Natural Earth 110m, gemeinfrei), wird sie gezeichnet; sonst zeigt die Karte Gradnetz und Städte.
"""

import json
import math
import os

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QSplitter, QToolTip, QApplication,
)

import styles
from i18n import tr
from widgets import make_table, set_rows, esc

BODY_BOXES = [
    ("Sun", "☉"), ("Moon", "☽"), ("Mercury", "☿"), ("Venus", "♀"), ("Mars", "♂"), ("Jupiter", "♃"),
    ("Saturn", "♄"), ("Uranus", "♅"), ("Neptune", "♆"), ("Pluto", "♇"), ("Chiron", "⚷"),
]
KIND_STYLE = {"MC": Qt.PenStyle.SolidLine, "IC": Qt.PenStyle.DashLine, "AC": Qt.PenStyle.SolidLine, "DC": Qt.PenStyle.DotLine}

LABEL_CITIES = ["London", "Paris", "Berlin", "Rom", "Moskau", "Kairo", "Dubai", "Neu-Delhi", "Peking", "Tokio", "Sydney",
                "Singapur", "Kapstadt", "Nairobi", "New York", "Los Angeles", "Mexiko-Stadt", "São Paulo", "Buenos Aires",
                "Lima", "Honolulu", "Anchorage", "Reykjavik", "Auckland", "Johannesburg", "Istanbul", "Bangkok"]


def _load_coastlines():
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "coastlines.geojson"), os.path.expanduser("~/.local/share/astrorust/coastlines.geojson"),
                 "/usr/share/astrorust/coastlines.geojson"):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    gj = json.load(f)
            except (OSError, ValueError):
                continue
            lines = []

            def add(coords):
                if coords and isinstance(coords[0][0], (int, float)):
                    lines.append([(c[0], c[1]) for c in coords])
                else:
                    for sub in coords:
                        add(sub)

            feats = gj.get("features", [gj]) if isinstance(gj, dict) else []
            for f in feats:
                geom = f.get("geometry", f)
                if geom and "coordinates" in geom:
                    add(geom["coordinates"])
            return lines
    return []


class WorldMap(QWidget):
    """Gleichwinklige Karte mit einheitlichem Maßstab (Länge und Breite gleich skaliert)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 280)
        self.setMouseTracking(True)
        self.lines = []
        self.cities = []
        self.label_cities = []
        self.coast = _load_coastlines()
        self.c_lon, self.c_lat, self.span = 0.0, 8.0, 360.0   # Mitte und sichtbare Längenspanne
        self.visible_bodies = None
        self.visible_kinds = {"MC", "IC", "AC", "DC"}
        self._drag = None
        self.marker = None

    def set_data(self, lines, cities, label_cities):
        self.lines, self.cities, self.label_cities = lines, cities, label_cities
        self.update()

    def reset_view(self):
        self.c_lon, self.c_lat, self.span = 0.0, 8.0, 360.0
        self.update()

    def center_on(self, lat, lon, span=40.0):
        self.c_lon, self.c_lat, self.span = lon, lat, span * 2
        self.marker = (lat, lon)
        self.update()

    @property
    def _scale(self):
        return self.width() / max(1e-9, self.span)  # Pixel pro Grad

    def _to_px(self, lat, lon):
        s = self._scale
        return QPointF(self.width() / 2 + (lon - self.c_lon) * s, self.height() / 2 - (lat - self.c_lat) * s)

    def _from_px(self, x, y):
        s = self._scale
        return (self.c_lat - (y - self.height() / 2) / s, self.c_lon + (x - self.width() / 2) / s)

    def _bounds(self):
        s = self._scale
        return (self.c_lon - self.width() / 2 / s, self.c_lon + self.width() / 2 / s,
                self.c_lat - self.height() / 2 / s, self.c_lat + self.height() / 2 / s)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#0d1117"))
        l0, l1, b0, b1 = self._bounds()
        # Kartenfläche (−180…180, −90…90) heller hinterlegen
        tl, br = self._to_px(90, -180), self._to_px(-90, 180)
        p.fillRect(QRectF(tl, br).normalized(), QColor("#12161b"))

        grid = 30 if self.span > 120 else (10 if self.span > 40 else 5)
        p.setFont(QFont("sans-serif", 8))
        for lon in range(-180, 181, grid):
            if l0 <= lon <= l1:
                x = self._to_px(0, lon).x()
                p.setPen(QPen(QColor(styles.BORDER_SOFT), 1))
                p.drawLine(QPointF(x, 0), QPointF(x, self.height()))
                p.setPen(QColor(styles.TEXT_DISABLED))
                p.drawText(QPointF(x + 2, self.height() - 3), f"{lon}°")
        for lat in range(-90, 91, grid):
            if b0 <= lat <= b1:
                y = self._to_px(lat, 0).y()
                p.setPen(QPen(QColor(styles.ACCENT_DARK if lat == 0 else styles.BORDER_SOFT), 1))
                p.drawLine(QPointF(0, y), QPointF(self.width(), y))
                p.setPen(QColor(styles.TEXT_DISABLED))
                p.drawText(QPointF(3, y - 2), f"{lat}°")

        # Land (falls coastlines.geojson vorhanden): Flächen leicht gefüllt, Küste hell
        if self.coast:
            p.setPen(QPen(QColor("#7b8794"), 1.1))
            p.setBrush(QBrush(QColor("#1f2933")))
            for ln in self.coast:
                if len(ln) < 3:
                    continue
                p.drawPolygon(QPolygonF([self._to_px(lat, lon) for lon, lat in ln]))

        # Städte
        p.setFont(QFont("sans-serif", 8))
        for c in self.cities:
            pt = self._to_px(c["latitude"], c["longitude"])
            if -4 <= pt.x() <= self.width() + 4 and -4 <= pt.y() <= self.height() + 4:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(styles.TEXT_DISABLED)))
                p.drawEllipse(pt, 1.6, 1.6)
        for c in self.label_cities:
            pt = self._to_px(c["latitude"], c["longitude"])
            if -4 <= pt.x() <= self.width() + 4 and -4 <= pt.y() <= self.height() + 4:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(styles.TEXT_MUTED)))
                p.drawEllipse(pt, 2.4, 2.4)
                if self.span <= 200:
                    p.setPen(QColor(styles.TEXT_MUTED))
                    p.drawText(pt + QPointF(5, 3), c["name"])

        # Linien
        for ln in self.lines:
            if not self._line_visible(ln):
                continue
            pen = QPen(QColor(ln["color_hex"]), 1.6)
            pen.setStyle(KIND_STYLE.get(ln["kind"], Qt.PenStyle.SolidLine))
            p.setPen(pen)
            for seg in ln["segments"]:
                pts = [self._to_px(la, lo) for la, lo in seg]
                for a, b in zip(pts, pts[1:]):
                    p.drawLine(a, b)
            seg = ln["segments"][0] if ln["segments"] else None
            if seg:
                stagger = (abs(hash(ln["body"])) % 5) * 11 / self._scale
                target_lat = min(b1, 85) - 6 / self._scale - stagger
                mid = min(seg, key=lambda q: abs(q[0] - target_lat))
                pt = self._to_px(mid[0], mid[1])
                if 0 <= pt.x() <= self.width() and 0 <= pt.y() <= self.height():
                    p.setFont(QFont("serif", 9, QFont.Weight.Bold))
                    p.setPen(QColor(ln["color_hex"]))
                    p.drawText(pt + QPointF(3, 11), f"{ln['glyph']}{ln['kind']}")

        if self.marker:
            pt = self._to_px(*self.marker)
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, 7, 7)

    def _line_visible(self, ln):
        if ln["kind"] not in self.visible_kinds:
            return False
        return self.visible_bodies is None or ln["body"] in self.visible_bodies

    # Interaktion: Mausrad = Zoom, Ziehen = Verschieben, Doppelklick = Gesamtansicht
    def wheelEvent(self, ev):
        factor = 0.8 if ev.angleDelta().y() > 0 else 1.25
        lat, lon = self._from_px(ev.position().x(), ev.position().y())
        new_span = min(360.0, max(8.0, self.span * factor))
        f = new_span / self.span
        self.c_lon = lon - (lon - self.c_lon) * f
        self.c_lat = lat - (lat - self.c_lat) * f
        self.span = new_span
        if self.span >= 360.0:
            self.c_lon = 0.0
        self.update()

    def mousePressEvent(self, ev):
        self._drag = (ev.position(), self.c_lon, self.c_lat)

    def mouseReleaseEvent(self, ev):
        self._drag = None

    def mouseDoubleClickEvent(self, ev):
        self.marker = None
        self.reset_view()

    def mouseMoveEvent(self, ev):
        if self._drag and ev.buttons():
            start, lon0, lat0 = self._drag
            s = self._scale
            self.c_lon = lon0 - (ev.position().x() - start.x()) / s
            self.c_lat = lat0 + (ev.position().y() - start.y()) / s
            self.update()
            return
        best, best_d = None, 7.0
        for ln in self.lines:
            if not self._line_visible(ln):
                continue
            for seg in ln["segments"]:
                pts = [self._to_px(la, lo) for la, lo in seg]
                for a, b in zip(pts, pts[1:]):
                    d = _dist_point_segment(ev.position(), a, b)
                    if d < best_d and abs(a.x() - b.x()) < self.width() / 2:
                        best, best_d = ln, d
        if best:
            QToolTip.showText(self.mapToGlobal(ev.pos()), f"<b>{esc(best['meaning'])}</b>", self)
        else:
            QToolTip.hideText()


def _dist_point_segment(p, a, b):
    ax, ay, bx, by = a.x(), a.y(), b.x(), b.y()
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(p.x() - ax, p.y() - ay)
    t = max(0.0, min(1.0, ((p.x() - ax) * dx + (p.y() - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p.x() - (ax + t * dx), p.y() - (ay + t * dy))


class AstroMapPanel(QWidget):
    def __init__(self, backend, get_request, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.get_request = get_request
        self.res = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Planeten:")))
        self.body_checks = {}
        for key, glyph in BODY_BOXES:
            c = QCheckBox(glyph)
            c.setChecked(key not in ("Chiron",))
            c.toggled.connect(self._apply_filter)
            row.addWidget(c)
            self.body_checks[key] = c
        row.addStretch()
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Linien:")))
        self.kind_checks = {}
        for kind in ("MC", "IC", "AC", "DC"):
            c = QCheckBox(kind)
            c.setChecked(True)
            c.toggled.connect(self._apply_filter)
            row.addWidget(c)
            self.kind_checks[kind] = c
        row.addStretch()
        b = QPushButton(tr("Karte berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run)
        row.addWidget(b)
        lay.addLayout(row)

        info = QLabel(tr("Mausrad: Zoom · Ziehen: Verschieben · Doppelklick: Gesamtansicht · Linie anfahren: Bedeutung. MC/IC = Beruf/Heim, AC/DC = Person/Beziehung."))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(info)

        sp = QSplitter(Qt.Orientation.Vertical)
        self.map = WorldMap()
        sp.addWidget(self.map)
        self.table = make_table(["Ort", "Land", "Linien", "Nächste Linie", "Abstand"], stretch_col=3)
        self.table.cellClicked.connect(self._on_city)
        sp.addWidget(self.table)
        sp.setSizes([360, 200])
        lay.addWidget(sp, 1)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(self.lbl_status)

    def _apply_filter(self):
        names = {"Sun": "Sonne", "Moon": "Mond", "Mercury": "Merkur", "Venus": "Venus", "Mars": "Mars", "Jupiter": "Jupiter",
                 "Saturn": "Saturn", "Uranus": "Uranus", "Neptune": "Neptun", "Pluto": "Pluto", "Chiron": "Chiron"}
        self.map.visible_bodies = {names[k] for k, c in self.body_checks.items() if c.isChecked()}
        self.map.visible_kinds = {k for k, c in self.kind_checks.items() if c.isChecked()}
        self.map.update()

    def run(self):
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.res = self.backend.call("astro_map", {"natal": self.get_request(), "city_orb": 2.0})
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as e:
            self.lbl_status.setText(str(e))
            return
        atlas = self.backend.search_cities("")
        labels = [c for c in atlas if c["name"] in LABEL_CITIES]
        self.map.set_data(self.res["lines"], atlas, labels)
        self._apply_filter()
        rows = []
        for c in self.res["cities"][:300]:
            h = c["hits"][0]
            rows.append([c["city"], c["country"], len(c["hits"]), f"{h['glyph']} {h['body']} {h['kind']}", f"{h['distance_deg']:.2f}°"])
        set_rows(self.table, rows)
        self.lbl_status.setText(f"{len(self.res['lines'])} {tr('Linien')} · {len(self.res['cities'])} {tr('Orte innerhalb von 2° einer Linie')}")

    def clear_results(self):
        self.res = None
        self.map.set_data([], [], [])
        self.map.marker = None
        self.table.setRowCount(0)
        self.lbl_status.clear()

    def _on_city(self, row, col):
        if not self.res or row >= len(self.res["cities"]):
            return
        c = self.res["cities"][row]
        self.map.center_on(c["latitude"], c["longitude"], 40.0)
        detail = " · ".join(f"{h['glyph']}{h['kind']} ({h['distance_deg']:.1f}°)" for h in c["hits"])
        self.lbl_status.setText(f"<b>{esc(c['city'])}</b>: {esc(detail)}")
