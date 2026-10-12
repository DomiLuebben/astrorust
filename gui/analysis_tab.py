# -*- coding: utf-8 -*-
"""
Astrorust — Analyse-Panel: klassische Würden, Aspektfiguren, Halbsummen / 90°-Scheibe,
arabische Lose, Fixsterne, Parallelen, Verteilung.
"""

import math

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QSplitter, QTextEdit, QGroupBox,
    QProgressBar, QCheckBox, QSizePolicy,
)

import styles
from i18n import tr
from widgets import make_table, set_rows, esc, tab_text


class DialWidget(QWidget):
    """90°-Scheibe (Hamburger Schule): Tierkreis modulo 90° auf einem Kreis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.entries = []
        self.highlight = None

    def set_entries(self, entries, highlight=None):
        self.entries = entries or []
        self.highlight = highlight
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(styles.WINDOW))
        if not self.entries:
            return
        size = min(w, h) - 20
        cx, cy = w / 2, h / 2
        r = size * 0.46

        p.setPen(QPen(QColor(styles.BORDER), 1.5))
        p.setBrush(QBrush(QColor(styles.SURFACE)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        def ang(pos):  # 0° oben, im Uhrzeigersinn; 90° Scheibe = voller Kreis
            return math.radians(pos * 4.0 - 90.0)

        for k in range(0, 90):
            a = ang(k)
            tick = 9 if k % 10 == 0 else (6 if k % 5 == 0 else 3)
            p.setPen(QPen(QColor(styles.TEXT_MUTED if k % 10 == 0 else styles.BORDER), 1.0))
            p.drawLine(QPointF(cx + r * math.cos(a), cy + r * math.sin(a)),
                       QPointF(cx + (r - tick) * math.cos(a), cy + (r - tick) * math.sin(a)))
            if k % 15 == 0:
                p.setFont(QFont("sans-serif", 8))
                p.setPen(QColor(styles.TEXT_MUTED))
                tx, ty = cx + (r + 12) * math.cos(a), cy + (r + 12) * math.sin(a)
                p.drawText(QRectF(tx - 14, ty - 8, 28, 16), Qt.AlignmentFlag.AlignCenter, f"{k}°")

        # Glyphen mit einfacher Abstoßung
        pts = sorted(self.entries, key=lambda e: e["position"])
        angles = [ang(e["position"]) for e in pts]
        draw = list(angles)
        for _ in range(10):
            for i in range(len(pts)):
                j = (i + 1) % len(pts)
                d = draw[j] - draw[i]
                if d < 0:
                    d += math.tau
                if d < 0.13 and len(pts) > 1:
                    s = (0.13 - d) / 2
                    draw[i] -= s
                    draw[j] += s
        for e, a_raw, a in zip(pts, angles, draw):
            rr = r - 26
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            hl = self.highlight and e["name"] in self.highlight
            p.setPen(QPen(QColor(styles.BORDER), 0.8))
            p.drawLine(QPointF(cx + (r - 9) * math.cos(a_raw), cy + (r - 9) * math.sin(a_raw)), QPointF(x, y))
            p.setBrush(QBrush(QColor(styles.ACCENT_DARK if hl else styles.SURFACE_RAISED)))
            p.setPen(QPen(QColor(styles.ACCENT if hl else styles.BORDER), 1.2))
            p.drawEllipse(QPointF(x, y), 12, 12)
            p.setFont(QFont("serif", 10 if len(e["glyph"]) == 1 else 7, QFont.Weight.Bold))
            p.setPen(QColor(styles.TEXT))
            p.drawText(QRectF(x - 12, y - 12, 24, 24), Qt.AlignmentFlag.AlignCenter, e["glyph"])


class AnalysisPanel(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis = None
        self.chart = None

        # 1. Würden
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        self.lbl_sect = QLabel("")
        self.lbl_sect.setStyleSheet(f"color: {styles.TEXT_MUTED}; font-size: 11px;")
        lay.addWidget(self.lbl_sect)
        self.table_dignities = make_table(
            ["Pt", "Planet", "Zeichen", "Domizil", "Erhöhung", "Triplizität (T/N/b)", "Grenze", "Dekanat", "Wertung", "Zustand"],
            stretch_col=9)
        lay.addWidget(self.table_dignities, 3)
        self.table_disp = make_table(["Pt", "Planet", "Zeichen", "Herrscher", "Herrscherkette"], stretch_col=4)
        lay.addWidget(self.table_disp, 3)
        self.lbl_rec = QLabel("")
        self.lbl_rec.setWordWrap(True)
        self.lbl_rec.setStyleSheet(f"font-size: 11px; color: {styles.TEXT_MUTED}; background:{styles.SURFACE_SUNKEN}; padding:6px; border-radius:4px;")
        lay.addWidget(self.lbl_rec)
        self.addTab(w, tr("Würden"))

        # 2. Figuren & Verteilung
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        self.lbl_shape = QLabel("")
        self.lbl_shape.setWordWrap(True)
        self.lbl_shape.setStyleSheet(f"background:{styles.SURFACE_SUNKEN}; padding:8px; border-radius:4px;")
        lay.addWidget(self.lbl_shape)
        self.table_patterns = make_table(["Figur", "Beteiligte", "Bedeutung"], stretch_col=2)
        lay.addWidget(self.table_patterns, 2)
        self.box_dist = QGroupBox(tr("Verteilung der zehn Planeten"))
        self.dist_layout = QVBoxLayout(self.box_dist)
        lay.addWidget(self.box_dist, 2)
        self.addTab(w, tab_text(tr("Figuren & Verteilung")))

        # 3. Halbsummen
        w = QWidget()
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.lbl_mid = QLabel(tr("Planetenbilder (Orbis 1°): Punkt steht auf der Halbsumme zweier anderer – direkt, im Quadrat oder in Opposition (90°-Scheibe)."))
        self.lbl_mid.setWordWrap(True)
        self.lbl_mid.setStyleSheet(f"color: {styles.TEXT_MUTED}; font-size: 11px;")
        ll.addWidget(self.lbl_mid)
        self.table_hits = make_table(["Bild", "Beziehung", "Orbis"], stretch_col=0)
        self.table_hits.itemSelectionChanged.connect(self._on_hit_selected)
        ll.addWidget(self.table_hits, 3)
        self.chk_all_mid = QCheckBox(tr("Alle Halbsummen zeigen"))
        self.chk_all_mid.toggled.connect(lambda on: self.table_mid.setVisible(on))
        ll.addWidget(self.chk_all_mid)
        self.table_mid = make_table(["Halbsumme", "Position"], stretch_col=1)
        self.table_mid.setVisible(False)
        ll.addWidget(self.table_mid, 2)
        sp.addWidget(left)
        self.dial = DialWidget()
        sp.addWidget(self.dial)
        sp.setSizes([320, 300])
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(sp)
        self.addTab(w, tr("Halbsummen"))

        # 4. Lose, Fixsterne, Parallelen
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(QLabel(f"<b>{tr('Arabische Lose (hellenistisch, mit Sektenumkehr)')}</b>"))
        self.table_lots = make_table(["Los", "Formel", "Position", "Haus"], stretch_col=1)
        lay.addWidget(self.table_lots, 3)
        lay.addWidget(QLabel(f"<b>{tr('Fixsterne in Konjunktion')}</b>"))
        self.table_stars = make_table(["Stern", "Position", "Kontakt", "Orbis", "Natur"], stretch_col=4)
        lay.addWidget(self.table_stars, 2)
        lay.addWidget(QLabel(f"<b>{tr('Parallelen (Deklination)')}</b>"))
        self.table_par = make_table(["Planet A", "Art", "Planet B", "Orbis"], stretch_col=0)
        lay.addWidget(self.table_par, 2)
        self.addTab(w, tr("Lose · Sterne · Parallelen"))

    # ── Daten ──
    def render(self, chart):
        self.chart = chart
        a = chart.get("analysis") if chart else None
        self.analysis = a
        enabled = bool(a)
        for i in range(self.count()):
            self.setTabEnabled(i, enabled)
        if not a:
            self.lbl_sect.setText(tr("Zusatzanalysen sind in den Einstellungen deaktiviert."))
            return

        diurnal = tr("Tageshoroskop (Sonne über dem Horizont)") if a.get("is_diurnal") else tr("Nachthoroskop (Sonne unter dem Horizont)")
        self.lbl_sect.setText(f"{tr('Sekte')}: {diurnal} — {tr('Wertung nach William Lilly: Domizil +5, Erhöhung +4, Triplizität +3, Grenze +2, Dekanat +1, Exil −5, Fall −4, peregrin −5')}")

        rows, colors = [], {}
        for i, d in enumerate(a["dignities"]):
            flags = lambda b: "●" if b else ""
            rows.append([
                d["glyph"], d["planet_name"], d["sign_name"],
                (flags(d["in_domicile"]) or d["domicile_ruler"]),
                (flags(d["in_exaltation"]) or (d["exaltation_ruler"] or "—")),
                f"{d['triplicity_day']}/{d['triplicity_night']}/{d['triplicity_participating']}" + ("  ●" if d["in_triplicity"] else ""),
                (flags(d["in_term"]) or d["term_ruler"]),
                (flags(d["in_face"]) or d["face_ruler"]),
                f"{d['score']:+d}", d["summary"],
            ])
            colors[(i, 8)] = styles.START_GREEN_HOVER if d["score"] > 0 else (styles.STOP_RED_HOVER if d["score"] < 0 else styles.TEXT)
        set_rows(self.table_dignities, rows, colors)

        set_rows(self.table_disp, [[x["glyph"], x["planet"], x["sign_name"], x["ruler"], x["chain"]] for x in a["dispositors"]])
        rec = [f"{r['planet_a']} ⇄ {r['planet_b']}: {r['kind']}" for r in a["receptions"]]
        fin = a.get("final_dispositor")
        txt = (tr("Enddispositor") + f": <b>{esc(fin)}</b><br>" if fin else tr("Kein einzelner Endpunkt (Herrscherzyklus).") + "<br>")
        txt += ("<br>".join(esc(r) for r in rec)) if rec else tr("Keine Rezeptionen.")
        self.lbl_rec.setText(txt)

        shape = a.get("chart_shape")
        self.lbl_shape.setText(
            f"<b>{tr('Horoskopform')}:</b> {esc(shape['name'])} ({shape['span_degrees']:.0f}°)<br>{esc(shape['description'])}" if shape else "")
        set_rows(self.table_patterns, [[p["name"], p["glyphs"], p["description"]] for p in a["patterns"]])

        # Verteilung
        while self.dist_layout.count():
            it = self.dist_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        dist = a["distribution"]

        def bar(label, value, total, color):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setMinimumWidth(170)
            row.addWidget(lbl)
            pb = QProgressBar()
            pb.setRange(0, max(1, total))
            pb.setValue(value)
            pb.setFormat(f"{value}")
            pb.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
            row.addWidget(pb)
            wdg = QWidget()
            wdg.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            self.dist_layout.addWidget(wdg)

        bar(tr("Über dem Horizont (7–12)"), dist["above_horizon"], 10, styles.COLOR_AIR)
        bar(tr("Unter dem Horizont (1–6)"), dist["below_horizon"], 10, styles.COLOR_WATER)
        bar(tr("Östliche Hälfte (10–3)"), dist["eastern"], 10, styles.ACCENT)
        bar(tr("Westliche Hälfte (4–9)"), dist["western"], 10, styles.COLOR_FIRE)
        for i, q in enumerate(dist["quadrants"]):
            bar(f"{tr('Quadrant')} {['I', 'II', 'III', 'IV'][i]} ({tr('Häuser')} {1+3*i}–{3+3*i})", q, 10, styles.COLOR_EARTH)
        lbl = QLabel(f"{tr('Betonte Häusergruppe')}: {dist['dominant_house_group']}")
        lbl.setStyleSheet(f"color: {styles.TEXT_MUTED};")
        self.dist_layout.addWidget(lbl)

        # Halbsummen
        rel = {0: tr("direkt"), 90: tr("im Quadrat"), 180: tr("in Opposition")}
        set_rows(self.table_hits, [[h["label"], rel.get(h["relation_degrees"], ""), h["formatted_orb"]] for h in a["midpoint_hits"]])
        self._hits = a["midpoint_hits"]
        set_rows(self.table_mid, [[m["label"], m["formatted"]] for m in a["midpoints"]])
        self.dial.set_entries(a["dial90"])

        # Lose, Sterne, Parallelen
        set_rows(self.table_lots, [[l["name"], l["formula"], f"{l['formatted']} {l['sign_name']}", f"{l['house']}."] for l in a["lots"]])
        set_rows(self.table_stars, [[s["star"], s["star_formatted"], f"{s['contact_glyph']} {s['contact']}", s["formatted_orb"], s["nature"]] for s in a["fixed_stars"]])
        set_rows(self.table_par, [[p["planet_a"], p["kind"], p["planet_b"], p["formatted_orb"]] for p in a["parallels"]])

    def _on_hit_selected(self):
        rows = self.table_hits.selectionModel().selectedRows()
        if not rows or not self.analysis:
            self.dial.set_entries(self.analysis["dial90"] if self.analysis else [])
            return
        h = self._hits[rows[0].row()]
        self.dial.set_entries(self.analysis["dial90"], highlight={h["point"], h["a"], h["b"]})
