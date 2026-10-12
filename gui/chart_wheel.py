# -*- coding: utf-8 -*-
"""
Astrorust — Natives Qt6 Horoskop-Rad Widget (QPainter Vektorgrafik)
"""

import math
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QRadialGradient, QCursor
)
from PyQt6.QtWidgets import QWidget, QToolTip

import styles


class ChartWheelWidget(QWidget):
    planet_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(420, 420)

        self.chart_data = None
        self.transit_data = None
        self.mode = "radix"  # "radix", "transit", "synastry"

        self.hovered_planet = None
        self.selected_planet = None
        self.hit_zones = []

    def set_data(self, chart_data, transit_data=None, mode="radix"):
        self.chart_data = chart_data
        self.transit_data = transit_data
        self.mode = mode
        self.update()

    def screen_angle(self, lon, asc):
        # Ascendant is fixed at left (180 deg / 9 o'clock)
        # Math angles: 0 is 3 o'clock (right), 90 is 6 o'clock (bottom), 180 is 9 o'clock (left), 270 is 12 o'clock
        diff = lon - asc
        deg = (180.0 - diff + 360.0) % 360.0
        return math.radians(deg)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor(styles.WINDOW))

        if not self.chart_data:
            painter.setPen(QColor(styles.TEXT_MUTED))
            painter.setFont(QFont("sans-serif", 13))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Bereit — Klicken Sie auf „Berechnen“")
            return

        w = self.width()
        h = self.height()
        size = min(w, h) - 20
        cx = w / 2.0
        cy = h / 2.0

        asc = self.chart_data.get("angles", {}).get("ascendant", 0.0)
        is_bi_wheel = (self.mode in ("transit", "synastry")) and bool(self.transit_data)

        # Radii definitions
        r_out = size * 0.47
        r_transit_in = r_out - (26 if is_bi_wheel else 0)
        r_zodiac_out = r_transit_in
        r_zodiac_in = r_zodiac_out - 28
        r_house_out = r_zodiac_in
        r_house_in = r_house_out - 46
        r_aspects = r_house_in - 4

        # 1. Background radial gradient
        grad = QRadialGradient(QPointF(cx, cy), r_out)
        grad.setColorAt(0.0, QColor("#1f242c"))
        grad.setColorAt(0.85, QColor(styles.SURFACE))
        grad.setColorAt(1.0, QColor(styles.WINDOW))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(styles.BORDER), 1.5))
        painter.drawEllipse(QPointF(cx, cy), r_out, r_out)

        # 2. Draw Zodiac Ring
        self._draw_zodiac_ring(painter, cx, cy, r_zodiac_out, r_zodiac_in, asc)

        # 3. Draw Houses Ring
        self._draw_houses(painter, cx, cy, r_house_out, r_house_in, asc)

        # 4. Draw Bi-Wheel Transit Ring if active
        if is_bi_wheel:
            self._draw_transit_ring(painter, cx, cy, r_out, r_transit_in, asc)

        # 5. Draw Aspects in central wheel
        self._draw_aspects(painter, cx, cy, r_aspects, asc)

        # 6. Draw Natal Planets with anti-collision spread
        self._draw_planets(painter, cx, cy, r_house_in + 23, asc)

        # 7. Center emblem
        painter.setBrush(QBrush(QColor(styles.SURFACE_RAISED)))
        painter.setPen(QPen(QColor(styles.ACCENT), 1.0))
        painter.drawEllipse(QPointF(cx, cy), 18, 18)
        painter.setFont(QFont("serif", 10))
        painter.setPen(QColor(styles.ACCENT))
        painter.drawText(QRectF(cx - 18, cy - 18, 36, 36), Qt.AlignmentFlag.AlignCenter, "✦")

    def _draw_zodiac_ring(self, painter, cx, cy, r_out, r_in, asc):
        signs = [
            ("♈", "Widder", styles.COLOR_FIRE),
            ("♉", "Stier", styles.COLOR_EARTH),
            ("♊", "Zwillinge", styles.COLOR_AIR),
            ("♋", "Krebs", styles.COLOR_WATER),
            ("♌", "Löwe", styles.COLOR_FIRE),
            ("♍", "Jungfrau", styles.COLOR_EARTH),
            ("♎", "Waage", styles.COLOR_AIR),
            ("♏", "Skorpion", styles.COLOR_WATER),
            ("♐", "Schütze", styles.COLOR_FIRE),
            ("♑", "Steinbock", styles.COLOR_EARTH),
            ("♒", "Wassermann", styles.COLOR_AIR),
            ("♓", "Fische", styles.COLOR_WATER),
        ]

        painter.setPen(QPen(QColor(styles.BORDER), 1.0))
        painter.drawEllipse(QPointF(cx, cy), r_out, r_out)
        painter.drawEllipse(QPointF(cx, cy), r_in, r_in)

        for i, (glyph, name, color_hex) in enumerate(signs):
            s_deg = i * 30.0
            mid_deg = s_deg + 15.0

            # Sign divider line
            a_start = self.screen_angle(s_deg, asc)
            x1 = cx + r_in * math.cos(a_start)
            y1 = cy + r_in * math.sin(a_start)
            x2 = cx + r_out * math.cos(a_start)
            y2 = cy + r_out * math.sin(a_start)

            painter.setPen(QPen(QColor(styles.BORDER_SOFT), 1.2))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Sign Glyph
            a_mid = self.screen_angle(mid_deg, asc)
            r_g = (r_out + r_in) / 2.0
            gx = cx + r_g * math.cos(a_mid)
            gy = cy + r_g * math.sin(a_mid)

            painter.setFont(QFont("serif", 13, QFont.Weight.Bold))
            painter.setPen(QColor(color_hex))
            painter.drawText(QRectF(gx - 14, gy - 14, 28, 28), Qt.AlignmentFlag.AlignCenter, glyph)

        # 360-degree ticks
        for deg in range(360):
            a = self.screen_angle(deg, asc)
            if deg % 10 == 0:
                tick = 5.0
                pen = QPen(QColor(styles.TEXT_MUTED), 1.0)
            elif deg % 5 == 0:
                tick = 3.5
                pen = QPen(QColor(styles.BORDER), 0.8)
            else:
                tick = 2.0
                pen = QPen(QColor(styles.BORDER_SOFT), 0.6)

            x1 = cx + r_out * math.cos(a)
            y1 = cy + r_out * math.sin(a)
            x2 = cx + (r_out - tick) * math.cos(a)
            y2 = cy + (r_out - tick) * math.sin(a)

            painter.setPen(pen)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_houses(self, painter, cx, cy, r_out, r_in, asc):
        houses = self.chart_data.get("houses", [])
        painter.setPen(QPen(QColor(styles.BORDER_SOFT), 1.0))
        painter.drawEllipse(QPointF(cx, cy), r_in, r_in)

        for i, h in enumerate(houses):
            lon = h.get("longitude", 0.0)
            num = h.get("house_number", i + 1)
            a = self.screen_angle(lon, asc)

            is_axis = num in (1, 4, 7, 10)
            pen_color = QColor(styles.ACCENT) if is_axis else QColor(styles.BORDER_SOFT)
            pen_w = 2.0 if is_axis else 1.0

            x1 = cx + r_in * math.cos(a)
            y1 = cy + r_in * math.sin(a)
            x2 = cx + r_out * math.cos(a)
            y2 = cy + r_out * math.sin(a)

            painter.setPen(QPen(pen_color, pen_w))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # House number label
            next_idx = (i + 1) % 12
            next_lon = houses[next_idx].get("longitude", 0.0)
            span = (next_lon - lon + 360.0) % 360.0
            mid_lon = (lon + span / 2.0) % 360.0
            a_mid = self.screen_angle(mid_lon, asc)

            r_num = r_in + 12.0
            nx = cx + r_num * math.cos(a_mid)
            ny = cy + r_num * math.sin(a_mid)

            painter.setFont(QFont("sans-serif", 8, QFont.Weight.Bold if is_axis else QFont.Weight.Normal))
            painter.setPen(QColor(styles.TEXT if is_axis else styles.TEXT_DISABLED))
            painter.drawText(QRectF(nx - 10, ny - 10, 20, 20), Qt.AlignmentFlag.AlignCenter, str(num))

        # AC and MC axis badges
        a_asc = self.screen_angle(self.chart_data.get("angles", {}).get("ascendant", 0.0), asc)
        painter.setFont(QFont("sans-serif", 9, QFont.Weight.Bold))
        painter.setPen(QColor(styles.ACCENT))
        ax = cx + (r_out + 12.0) * math.cos(a_asc)
        ay = cy + (r_out + 12.0) * math.sin(a_asc)
        painter.drawText(QRectF(ax - 12, ay - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, "AC")

        a_mc = self.screen_angle(self.chart_data.get("angles", {}).get("midheaven", 0.0), asc)
        mx = cx + (r_out + 12.0) * math.cos(a_mc)
        my = cy + (r_out + 12.0) * math.sin(a_mc)
        painter.drawText(QRectF(mx - 12, my - 10, 24, 20), Qt.AlignmentFlag.AlignCenter, "MC")

    def _draw_aspects(self, painter, cx, cy, r_aspects, asc):
        planets = self.chart_data.get("planets", [])
        aspects = self.chart_data.get("aspects", [])

        planets_map = {p["id"]: p for p in planets}

        for asp in aspects:
            p1 = planets_map.get(asp.get("point_a"))
            p2 = planets_map.get(asp.get("point_b"))
            if not p1 or not p2:
                continue

            a1 = self.screen_angle(p1["longitude"], asc)
            a2 = self.screen_angle(p2["longitude"], asc)

            x1 = cx + r_aspects * math.cos(a1)
            y1 = cy + r_aspects * math.sin(a1)
            x2 = cx + r_aspects * math.cos(a2)
            y2 = cy + r_aspects * math.sin(a2)

            is_highlight = False
            if self.hovered_planet:
                h_id = self.hovered_planet.get("id")
                if h_id in (asp.get("point_a"), asp.get("point_b")):
                    is_highlight = True

            orb = asp.get("orb", 5.0)
            color_hex = asp.get("color_hex", styles.ACCENT)
            qcolor = QColor(color_hex)

            if self.hovered_planet and not is_highlight:
                qcolor.setAlpha(25)  # Dim
                pen_w = 0.8
            else:
                qcolor.setAlpha(230 if is_highlight else (190 if orb <= 1.5 else 120))
                pen_w = 2.2 if is_highlight else (1.6 if orb <= 1.0 else 1.0)

            painter.setPen(QPen(qcolor, pen_w))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    def _draw_planets(self, painter, cx, cy, r_base, asc):
        planets = self.chart_data.get("planets", [])
        self.hit_zones = []

        # Anti-collision spreading algorithm
        items = []
        for p in planets:
            raw_a = self.screen_angle(p["longitude"], asc)
            items.append({
                "planet": p,
                "raw_angle": raw_a,
                "draw_angle": raw_a,
                "radius": r_base,
            })

        items.sort(key=lambda x: x["raw_angle"])

        min_spacing = 0.13  # radians (~7.5 deg)
        for _ in range(8):
            for i in range(len(items)):
                j = (i + 1) % len(items)
                diff = items[j]["draw_angle"] - items[i]["draw_angle"]
                if diff < 0:
                    diff += math.tau
                if diff < min_spacing:
                    shift = (min_spacing - diff) / 2.0
                    items[i]["draw_angle"] -= shift
                    items[j]["draw_angle"] += shift
                    items[j]["radius"] = r_base + (10 if i % 2 == 0 else -8)

        for item in items:
            p = item["planet"]
            is_hover = self.hovered_planet and (self.hovered_planet.get("id") == p.get("id"))
            r = item["radius"]
            da = item["draw_angle"]

            px = cx + r * math.cos(da)
            py = cy + r * math.sin(da)

            # Store hit zone for mouse clicks
            self.hit_zones.append({
                "planet": p,
                "x": px,
                "y": py,
                "radius": 13,
            })

            # Connector tick if shifted
            if abs(item["draw_angle"] - item["raw_angle"]) > 0.02:
                tx = cx + (r_base - 14) * math.cos(item["raw_angle"])
                ty = cy + (r_base - 14) * math.sin(item["raw_angle"])
                painter.setPen(QPen(QColor(styles.BORDER), 0.8))
                painter.drawLine(QPointF(tx, ty), QPointF(px, py))

            # Planet Badge background
            bg_color = QColor(styles.ACCENT_DARK if is_hover else styles.SURFACE_RAISED)
            border_color = QColor(styles.ACCENT if is_hover else styles.BORDER)
            painter.setBrush(QBrush(bg_color))
            painter.setPen(QPen(border_color, 1.5 if is_hover else 1.0))
            painter.drawEllipse(QPointF(px, py), 11, 11)

            # Planet Glyph
            glyph = p.get("glyph", "•")
            painter.setFont(QFont("serif", 11, QFont.Weight.Bold))
            painter.setPen(QColor("#ffffff" if is_hover else styles.TEXT))
            painter.drawText(QRectF(px - 11, py - 11, 22, 22), Qt.AlignmentFlag.AlignCenter, glyph)

            # Retrograde sign
            if p.get("is_retrograde", False):
                painter.setFont(QFont("sans-serif", 7, QFont.Weight.Bold))
                painter.setPen(QColor(styles.STOP_RED))
                painter.drawText(QRectF(px + 6, py - 12, 12, 12), Qt.AlignmentFlag.AlignCenter, "℞")

    def _draw_transit_ring(self, painter, cx, cy, r_out, r_in, asc):
        transit_planets = self.transit_data.get("planets", [])
        painter.setPen(QPen(QColor(styles.ACCENT_DARK), 1.0))
        painter.drawEllipse(QPointF(cx, cy), r_out, r_out)

        r_mid = (r_out + r_in) / 2.0
        for p in transit_planets:
            a = self.screen_angle(p["longitude"], asc)
            px = cx + r_mid * math.cos(a)
            py = cy + r_mid * math.sin(a)

            painter.setBrush(QBrush(QColor(styles.SURFACE_SUNKEN)))
            painter.setPen(QPen(QColor(styles.ACCENT), 1.2))
            painter.drawEllipse(QPointF(px, py), 9, 9)

            glyph = p.get("glyph", "•")
            painter.setFont(QFont("serif", 9, QFont.Weight.Bold))
            painter.setPen(QColor(styles.ACCENT))
            painter.drawText(QRectF(px - 9, py - 9, 18, 18), Qt.AlignmentFlag.AlignCenter, glyph)

    def mouseMoveEvent(self, event):
        pos = event.position()
        mx = pos.x()
        my = pos.y()

        hit = None
        for z in self.hit_zones:
            dx = mx - z["x"]
            dy = my - z["y"]
            if math.hypot(dx, dy) <= z["radius"]:
                hit = z["planet"]
                break

        if hit != self.hovered_planet:
            self.hovered_planet = hit
            self.update()

            if hit:
                self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                tip_text = (
                    f"<b>{hit.get('glyph')} {hit.get('name')}</b><br>"
                    f"Position: {hit.get('formatted_deg')} in {hit.get('sign_name')} ({hit.get('sign_glyph')})<br>"
                    f"Haus: {hit.get('house')}. Haus<br>"
                    f"{'Rückläufig ℞<br>' if hit.get('is_retrograde') else ''}"
                    f"{'Würde: ' + hit.get('dignity') + '<br>' if hit.get('dignity') else ''}"
                    f"Geschwindigkeit: {hit.get('speed', 0.0):.3f}°/Tag"
                )
                QToolTip.showText(self.mapToGlobal(event.pos()), tip_text, self)
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                QToolTip.hideText()

    def mousePressEvent(self, event):
        if self.hovered_planet:
            self.selected_planet = self.hovered_planet
            self.planet_selected.emit(self.selected_planet)
