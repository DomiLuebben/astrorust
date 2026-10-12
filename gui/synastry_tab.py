# -*- coding: utf-8 -*-
"""
Astrorust — Synastrie-Panel: Aspektgitter, Liste, Häuserüberlagerung, Composite, Davison, Deutung.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QSplitter, QHeaderView, QAbstractItemView,
)

import styles
from i18n import tr
from widgets import make_table, set_rows, esc


class SynastryPanel(QTabWidget):
    # "composite" / "davison": Chart zeigen; "partner": Partner im Außenring
    showChart = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None

        # Gitter
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        self.lbl_grid = QLabel("")
        self.lbl_grid.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(self.lbl_grid)
        self.grid = QTableWidget()
        self.grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.grid.cellClicked.connect(self._on_grid_click)
        lay.addWidget(self.grid, 1)
        self.lbl_cell = QLabel("")
        self.lbl_cell.setStyleSheet(f"font-size: 11px; color:{styles.TEXT_MUTED}; background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px;")
        lay.addWidget(self.lbl_cell)
        self.addTab(w, tr("Aspektgitter"))

        # Liste
        self.table_cross = make_table(["A", "Aspekt", "B", "Orbis", ""], stretch_col=1)
        self.addTab(self.table_cross, tr("Aspekte A↔B"))

        # Überlagerung
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        left = QVBoxLayout()
        self.lbl_ov_a = QLabel("")
        left.addWidget(self.lbl_ov_a)
        self.table_ov_a = make_table(["Pt", "Planet A", "Zeichen", "Haus bei B"], stretch_col=2)
        left.addWidget(self.table_ov_a)
        right = QVBoxLayout()
        self.lbl_ov_b = QLabel("")
        right.addWidget(self.lbl_ov_b)
        self.table_ov_b = make_table(["Pt", "Planet B", "Zeichen", "Haus bei A"], stretch_col=2)
        right.addWidget(self.table_ov_b)
        lay.addLayout(left)
        lay.addLayout(right)
        self.addTab(w, tr("Häuserüberlagerung"))

        # Composite
        self.table_comp, self.btn_comp, self.lbl_comp, wc = self._chart_tab(
            tr("Composite (Halbsummen): jeder Punkt ist der Mittelpunkt der beiden Radixpunkte; das Horoskop beschreibt die Beziehung als eigene Wesenheit."), "composite")
        self.addTab(wc, tr("Composite"))
        # Davison
        self.table_dav, self.btn_dav, self.lbl_dav, wd = self._chart_tab(
            tr("Davison: reales Horoskop für den Mittelpunkt in Zeit und Ort beider Geburten."), "davison")
        self.addTab(wd, tr("Davison"))

        # Deutung
        self.text_notes = QTextEdit()
        self.text_notes.setReadOnly(True)
        self.addTab(self.text_notes, tr("Deutung"))

    def _chart_tab(self, hint, kind):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lbl = QLabel(hint)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(lbl)
        info = QLabel("")
        info.setWordWrap(True)
        lay.addWidget(info)
        btn = QPushButton(tr("Als Horoskoprad anzeigen"))
        btn.setObjectName("btn_start")
        btn.clicked.connect(lambda: self._emit(kind))
        lay.addWidget(btn)
        table = make_table(["Pt", "Punkt", "Position", "Haus"], stretch_col=2)
        lay.addWidget(table, 1)
        return table, btn, info, w

    def _emit(self, kind):
        if not self.result:
            return
        chart = self.result.get("composite_chart" if kind == "composite" else "davison_chart")
        if chart:
            self.showChart.emit(kind, chart)

    def clear_results(self):
        self.result = None
        for table in self.findChildren(QTableWidget):
            table.setRowCount(0)
        for label in (self.lbl_grid, self.lbl_cell, self.lbl_ov_a, self.lbl_ov_b, self.lbl_comp, self.lbl_dav):
            label.clear()
        self.text_notes.clear()
        self.btn_comp.setEnabled(False)
        self.btn_dav.setEnabled(False)

    def render(self, res):
        self.result = res
        a, b = res["chart_a"], res["chart_b"]
        g = res["grid"]

        # Gitter
        rows, cols = len(g["rows"]), len(g["cols"])
        self.grid.clear()
        self.grid.setRowCount(rows)
        self.grid.setColumnCount(cols)
        self.grid.setHorizontalHeaderLabels(g["col_glyphs"])
        self.grid.setVerticalHeaderLabels(g["row_glyphs"])
        for r in range(rows):
            for c in range(cols):
                cell = g["cells"][r][c]
                item = QTableWidgetItem(cell["aspect_glyph"] if cell else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if cell:
                    item.setForeground(QColor(cell["color_hex"]))
                    item.setData(Qt.ItemDataRole.UserRole, (r, c))
                self.grid.setItem(r, c, item)
        self.grid.resizeColumnsToContents()
        self.grid.resizeRowsToContents()
        self.lbl_grid.setText(f"{tr('Zeilen')}: {esc(a['name'])} · {tr('Spalten')}: {esc(b['name'])}")
        self.lbl_cell.setText(tr("Zelle anklicken für Details."))

        # Liste
        asp = res["cross_aspects"]
        set_rows(self.table_cross, [
            [f"{x['transit_glyph']} {x['transit_name']}", f"{x['aspect_glyph']} {x['aspect_name']}",
             f"{x['natal_glyph']} {x['natal_name']}", x["formatted_orb"], "→" if x.get("is_applying") else "←"] for x in asp],
            {(i, 1): x["color_hex"] for i, x in enumerate(asp)})

        # Überlagerung
        glyph = {p["name"]: p["glyph"] for p in a["planets"] + b["planets"]}
        set_rows(self.table_ov_a, [[glyph.get(o["planet"], o["glyph"]), o["planet"], o["sign_name"], f"{o['house']}."] for o in res["overlay_a_in_b"]])
        set_rows(self.table_ov_b, [[glyph.get(o["planet"], o["glyph"]), o["planet"], o["sign_name"], f"{o['house']}."] for o in res["overlay_b_in_a"]])
        self.lbl_ov_a.setText(f"<b>{esc(a['name'])}</b> {tr('in den Häusern von')} <b>{esc(b['name'])}</b>")
        self.lbl_ov_b.setText(f"<b>{esc(b['name'])}</b> {tr('in den Häusern von')} <b>{esc(a['name'])}</b>")

        for key, table, info, btn in (("composite_chart", self.table_comp, self.lbl_comp, self.btn_comp),
                                       ("davison_chart", self.table_dav, self.lbl_dav, self.btn_dav)):
            ch = res.get(key)
            btn.setEnabled(bool(ch))
            if ch:
                info.setText(f"<b>{esc(ch['name'])}</b> — {esc(ch['date_time'])} · {esc(ch['location_name'])}<br>"
                             f"AC {esc(ch['angles']['ascendant_formatted'])} · MC {esc(ch['angles']['midheaven_formatted'])}")
                set_rows(table, [[p["glyph"], p["name"], f"{p['formatted_deg']} {p['sign_glyph']}", f"{p['house']}."] for p in ch["planets"]])
            else:
                info.setText(tr("Nicht berechenbar."))
                table.setRowCount(0)

        html = ""
        for sec in res.get("compatibility_notes", []):
            html += f"<h3 style='color:{styles.ACCENT}; margin-bottom:2px;'>{esc(sec.get('title'))}</h3>"
            html += f"<div style='color:{styles.TEXT_MUTED}; font-size:10px;'>{esc(sec.get('subtitle'))}</div>"
            html += f"<p style='margin-top:4px;'>{esc(sec.get('text'))}</p>"
            html += f"<div style='color:{styles.COLOR_AIR}; font-size:10px;'>{esc(' • '.join(sec.get('keywords', [])))}</div><hr>"
        self.text_notes.setHtml(html)

    def _on_grid_click(self, r, c):
        if not self.result:
            return
        cell = self.result["grid"]["cells"][r][c]
        g = self.result["grid"]
        if cell:
            self.lbl_cell.setText(f"<b>{esc(g['rows'][r])} {cell['aspect_glyph']} {esc(cell['aspect_name'])} {esc(g['cols'][c])}</b> — {tr('Orbis')} {cell['formatted_orb']}")
        else:
            self.lbl_cell.setText(f"{esc(g['rows'][r])} / {esc(g['cols'][c])}: {tr('kein Aspekt')}")
