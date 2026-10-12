# -*- coding: utf-8 -*-
"""
Astrorust — Vedisches Panel: Rashi-Tafel (südindisch / nordindisch), Grahas mit Nakshatra,
Vargas (D1–D12), Vimshottari-Dasha.
"""

from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QSplitter, QApplication,
)

import styles
from i18n import tr
from widgets import compact_combo, make_table, set_rows, esc

ABBR = {"☉": "Su", "☽": "Mo", "♂": "Ma", "☿": "Me", "♃": "Ju", "♀": "Ve", "♄": "Sa", "☊": "Ra", "☋": "Ke"}

# Südindische Tafel: Rashi-Index (0 = Widder) → (Zeile, Spalte)
SOUTH_POS = {11: (0, 0), 0: (0, 1), 1: (0, 2), 2: (0, 3), 3: (1, 3), 4: (2, 3), 5: (3, 3),
             6: (3, 2), 7: (3, 1), 8: (3, 0), 9: (2, 0), 10: (1, 0)}

# Nordindische Tafel: Haus → Eckpunkte im Einheitsquadrat (gegen den Uhrzeigersinn ab oben)
NORTH_POLY = {
    1: [(0.5, 0.5), (0.25, 0.25), (0.5, 0.0), (0.75, 0.25)],
    2: [(0.0, 0.0), (0.5, 0.0), (0.25, 0.25)],
    3: [(0.0, 0.0), (0.25, 0.25), (0.0, 0.5)],
    4: [(0.5, 0.5), (0.25, 0.25), (0.0, 0.5), (0.25, 0.75)],
    5: [(0.0, 0.5), (0.25, 0.75), (0.0, 1.0)],
    6: [(0.0, 1.0), (0.25, 0.75), (0.5, 1.0)],
    7: [(0.5, 0.5), (0.25, 0.75), (0.5, 1.0), (0.75, 0.75)],
    8: [(0.5, 1.0), (0.75, 0.75), (1.0, 1.0)],
    9: [(1.0, 1.0), (0.75, 0.75), (1.0, 0.5)],
    10: [(0.5, 0.5), (0.75, 0.75), (1.0, 0.5), (0.75, 0.25)],
    11: [(1.0, 0.5), (0.75, 0.25), (1.0, 0.0)],
    12: [(1.0, 0.0), (0.75, 0.25), (0.5, 0.0)],
}


class RashiChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.style_name = "south"
        self.lagna = 0
        self.by_sign = {}
        self.title = ""

    def set_data(self, varga, retro_names, style_name):
        self.style_name = style_name
        self.lagna = varga["lagna_rashi_index"]
        self.title = f"{varga['key']} · {varga['name']}"
        self.by_sign = {}
        for pl in varga["placements"]:
            abbr = ABBR.get(pl["glyph"], pl["glyph"])
            if pl["point"] in retro_names:
                abbr += "ᴿ"
            self.by_sign.setdefault(pl["rashi_index"], []).append(abbr)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(styles.WINDOW))
        size = min(self.width(), self.height()) - 20
        ox, oy = (self.width() - size) / 2, (self.height() - size) / 2
        p.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
        p.setPen(QColor(styles.ACCENT))
        p.drawText(QRectF(ox, oy - 6, size, 16), Qt.AlignmentFlag.AlignCenter, self.title)
        oy += 12
        size -= 12
        if self.style_name == "south":
            self._south(p, ox, oy, size)
        else:
            self._north(p, ox, oy, size)

    def _planet_text(self, rashi):
        return "  ".join(self.by_sign.get(rashi, []))

    def _south(self, p, ox, oy, size):
        cell = size / 4
        pen = QPen(QColor(styles.BORDER), 1.5)
        for rashi, (r, c) in SOUTH_POS.items():
            rect = QRectF(ox + c * cell, oy + r * cell, cell, cell)
            p.setPen(pen)
            p.setBrush(QBrush(QColor(styles.SURFACE)))
            p.drawRect(rect)
            if rashi == self.lagna:
                p.setPen(QPen(QColor(styles.ACCENT), 1.8))
                p.drawLine(rect.topLeft(), rect.topLeft() + QPointF(cell * 0.28, cell * 0.28))
                p.setFont(QFont("sans-serif", 7))
                p.drawText(rect.adjusted(3, 12, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "Lg")
            p.setFont(QFont("serif", 12))
            p.setPen(QColor(styles.TEXT_DISABLED))
            glyph = "♈♉♊♋♌♍♎♏♐♑♒♓"[rashi] + "\uFE0E"
            p.drawText(rect.adjusted(0, 0, -4, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop, glyph)
            p.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))
            p.setPen(QColor(styles.TEXT))
            p.drawText(rect.adjusted(4, 14, -4, -4), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._planet_text(rashi))
        p.setPen(QColor(styles.TEXT_MUTED))
        p.setFont(QFont("sans-serif", 9))
        p.drawText(QRectF(ox + cell, oy + cell, 2 * cell, 2 * cell), Qt.AlignmentFlag.AlignCenter, tr("Rashi"))

    def _north(self, p, ox, oy, size):
        pen = QPen(QColor(styles.BORDER), 1.5)
        for house, pts in NORTH_POLY.items():
            poly = QPolygonF([QPointF(ox + x * size, oy + y * size) for x, y in pts])
            p.setPen(pen)
            p.setBrush(QBrush(QColor(styles.SURFACE)))
            p.drawPolygon(poly)
            cx = sum(x for x, _ in pts) / len(pts)
            cy = sum(y for _, y in pts) / len(pts)
            rashi = (self.lagna + house - 1) % 12
            p.setFont(QFont("sans-serif", 8))
            p.setPen(QColor(styles.ACCENT if house == 1 else styles.TEXT_DISABLED))
            # Rashi-Nummer nahe der Ecke zur Mitte
            p.drawText(QPointF(ox + cx * size - 5, oy + cy * size - 12), str(rashi + 1))
            p.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
            p.setPen(QColor(styles.TEXT))
            area = QRectF(ox + cx * size - 34, oy + cy * size - 8, 68, 30)
            p.drawText(area, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self._planet_text(rashi))


class VedicPanel(QWidget):
    def __init__(self, backend, get_request, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.get_request = get_request
        self.res = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Ayanamsa:")))
        self.combo_ayan = compact_combo(QComboBox(), 12)
        try:
            for a in backend.call("ayanamsas"):
                self.combo_ayan.addItem(a["name"], a["id"])
        except Exception:
            self.combo_ayan.addItem("Lahiri", 1)
        row.addWidget(self.combo_ayan, 1)
        row.addWidget(QLabel(tr("Rahu/Ketu:")))
        self.combo_node = compact_combo(QComboBox(), 10)
        self.combo_node.addItem(tr("Mittlerer Knoten"), "Mean")
        self.combo_node.addItem(tr("Wahrer Knoten"), "True")
        row.addWidget(self.combo_node)
        lay.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel(tr("Tafel:")))
        self.combo_style = compact_combo(QComboBox(), 10)
        self.combo_style.addItem(tr("Südindisch"), "south")
        self.combo_style.addItem(tr("Nordindisch"), "north")
        self.combo_style.currentIndexChanged.connect(self._redraw)
        row.addWidget(self.combo_style)
        self.combo_varga = compact_combo(QComboBox(), 10)
        self.combo_varga.currentIndexChanged.connect(self._redraw)
        row.addWidget(self.combo_varga, 1)
        b = QPushButton(tr("Berechnen"))
        b.setObjectName("btn_start")
        b.clicked.connect(self.run)
        row.addWidget(b)
        lay.addLayout(row)

        self.lbl_head = QLabel("")
        self.lbl_head.setWordWrap(True)
        self.lbl_head.setStyleSheet(f"background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px;")
        lay.addWidget(self.lbl_head)

        sp = QSplitter(Qt.Orientation.Horizontal)
        self.chart = RashiChart()
        sp.addWidget(self.chart)
        tabs = QTabWidget()
        self.table_pl = make_table(["Graha", "Name", "Position", "Rashi", "Haus", "Nakshatra", "Pada", "Herr", "Würde", "Navamsa"], stretch_col=5)
        tabs.addTab(self.table_pl, tr("Grahas"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Dasha / Bhukti"), tr("Beginn"), tr("Ende"), tr("Jahre")])
        self.tree.setColumnWidth(0, 180)
        tabs.addTab(self.tree, tr("Vimshottari-Dasha"))
        sp.addWidget(tabs)
        sp.setSizes([360, 560])
        lay.addWidget(sp, 1)

    def run(self):
        try:
            req = self.get_request()
            settings = dict(req.get("settings") or {})
            settings.update({"zodiac": "Sidereal", "ayanamsa": int(self.combo_ayan.currentData()), "node": self.combo_node.currentData(),
                             "fixed_stars": False, "analysis": False, "south_node": True})
            req["settings"] = settings
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self.res = self.backend.call("vedic", {"natal": req})
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as e:
            self.lbl_head.setText(f"<span style='color:{styles.STOP_RED}'>{esc(e)}</span>")
            return
        r = self.res
        self.lbl_head.setText(
            f"<b>{esc(r['chart']['name'])}</b> — Lagna: <b>{esc(r['lagna'])}</b> · Mond-Nakshatra: <b>{esc(r['moon_nakshatra'])}</b> · "
            f"Ayanamsa {esc(r['ayanamsa_name'])}: {r['ayanamsa_value']:.4f}° · {esc(r['dasha_system'])}")
        self.combo_varga.blockSignals(True)
        self.combo_varga.clear()
        for v in r["vargas"]:
            self.combo_varga.addItem(f"{v['key']} {v['name']}", v["key"])
            self.combo_varga.setItemData(self.combo_varga.count() - 1, v["meaning"], Qt.ItemDataRole.ToolTipRole)
        self.combo_varga.blockSignals(False)

        rows = []
        for p in r["planets"]:
            rows.append([p["glyph"], f"{p['name']} ({p['sanskrit']})" + (" ℞" if p["retrograde"] and p["id"] not in ("TrueNode", "SouthNode") else ""),
                         p["formatted"], f"{p['rashi']} ({p['rashi_sanskrit']})", f"{p['house']}.", p["nakshatra"], p["pada"],
                         p["nakshatra_lord"], p["dignity"], p["navamsa_rashi"]])
        set_rows(self.table_pl, rows)

        self.tree.clear()
        for d in r["dasha"]:
            top = QTreeWidgetItem([d["lord"], d["start"], d["end"], f"{d['years']:.1f}"])
            if d["current"]:
                for col in range(4):
                    top.setForeground(col, QColor(styles.START_GREEN_HOVER))
                top.setExpanded(True)
            for s in d["sub_periods"]:
                child = QTreeWidgetItem([f"{d['lord']} / {s['lord']}", s["start"], s["end"], f"{s['years']:.2f}"])
                if s["current"]:
                    for col in range(4):
                        child.setForeground(col, QColor(styles.START_GREEN_HOVER))
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            if d["current"]:
                self.tree.expandItem(top)
        self._redraw()

    def clear_results(self):
        self.res = None
        self.table_pl.setRowCount(0)
        self.tree.clear()
        self.combo_varga.clear()
        self.lbl_head.clear()
        self.chart.by_sign = {}
        self.chart.title = ""
        self.chart.update()

    def _redraw(self):
        if not self.res:
            return
        key = self.combo_varga.currentData()
        varga = next((v for v in self.res["vargas"] if v["key"] == key), self.res["vargas"][0])
        retro = {p["name"] for p in self.res["planets"] if p["retrograde"] and p["id"] not in ("TrueNode", "SouthNode")}
        self.chart.set_data(varga, retro, self.combo_style.currentData())
