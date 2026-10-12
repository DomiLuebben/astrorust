# -*- coding: utf-8 -*-
"""
Astrorust — PDF-Bericht (Rad, Tabellen, Deutung, Analyse, KI-Text) über QPdfWriter/QTextDocument.
"""

import base64

from PyQt6.QtCore import QMarginsF, QRectF, QBuffer, QIODevice
from PyQt6.QtGui import QImage, QPainter, QPdfWriter, QPageSize, QPageLayout, QTextDocument, QColor

from i18n import tr
from widgets import esc

CSS = """
body { font-family: 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 9.5pt; color: #111; }
h1 { font-size: 20pt; margin: 0 0 4px 0; color: #1d4f73; }
h2 { font-size: 13pt; margin: 14px 0 4px 0; color: #1d4f73; border-bottom: 1px solid #9ab; }
h3 { font-size: 10.5pt; margin: 8px 0 2px 0; }
table { border-collapse: collapse; width: 100%; }
th { text-align: left; background: #e6eef4; padding: 2px 5px; font-size: 8.5pt; }
td { padding: 2px 5px; border-bottom: 1px solid #dde; font-size: 8.5pt; }
.muted { color: #667; font-size: 8.5pt; }
"""


def _png_data_uri(image: QImage) -> str:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(bytes(buf.data())).decode("ascii")


def render_wheel_image(wheel, size=1500, chart=None) -> QImage:
    """Render at print resolution while preserving readable glyph sizes."""
    if chart is not None:
        from chart_wheel import ChartWheelWidget
        wheel = ChartWheelWidget()
        wheel.set_data(chart)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor("#1a1d20"))
    p = QPainter(img)
    logical_size = 520
    p.scale(size / logical_size, size / logical_size)
    wheel.paint_wheel(p, QRectF(0, 0, logical_size, logical_size))
    p.end()
    return img


def table_html(headers, rows):
    out = "<table><tr>" + "".join(f"<th>{esc(h)}</th>" for h in headers) + "</tr>"
    for r in rows:
        out += "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>"
    return out + "</table>"


def build_report_html(chart, wheel_image, sections, ai_markdown=None):
    c = chart
    html = f"<html><head><style>{CSS}</style></head><body>"
    html += f"<h1>{esc(c['name'])}</h1>"
    html += f"<div class='muted'>{esc(c['date_time'])} · {esc(c['location_name'])} · {esc(c['house_system'])}"
    if c.get("zodiac") == "Sidereal" and c.get("ayanamsa_name"):
        html += f" · {tr('siderisch')} ({esc(c['ayanamsa_name'])})"
    html += "</div>"
    tzinfo = c.get("timezone_info")
    if tzinfo:
        html += f"<div class='muted'>{esc(tzinfo['note'])}</div>"
    if wheel_image is not None:
        html += f"<p align='center'><img src='{_png_data_uri(wheel_image)}' width='520'></p>"
    ang = c["angles"]
    html += (f"<p><b>AC</b> {esc(ang['ascendant_formatted'])} · <b>MC</b> {esc(ang['midheaven_formatted'])} · "
             f"<b>DC</b> {esc(ang['descendant_formatted'])} · <b>IC</b> {esc(ang['imum_coeli_formatted'])} · "
             f"<b>⊗</b> {esc(ang['part_of_fortune_formatted'])}</p>")

    html += f"<h2>{tr('Planeten')}</h2>"
    html += table_html([tr("Punkt"), tr("Position"), tr("Haus"), tr("Würde"), "℞"],
                       [[f"{p['glyph']} {p['name']}", f"{p['formatted_deg']} {p['sign_name']}", f"{p['house']}.",
                         p.get("dignity") or "—", "℞" if p["is_retrograde"] else ""] for p in c["planets"]])
    html += f"<h2>{tr('Häuserspitzen')}</h2>"
    html += table_html([tr("Haus"), tr("Zeichen"), tr("Position")],
                       [[f"{h['house_number']}.", h["sign_name"], h["formatted_deg"]] for h in c["houses"]])
    html += f"<h2>{tr('Aspekte')}</h2>"
    html += table_html([tr("Punkt A"), tr("Aspekt"), tr("Punkt B"), tr("Orbis"), ""],
                       [[f"{a['point_a_glyph']} {a['point_a_name']}", f"{a['aspect_glyph']} {a['aspect_name']}",
                         f"{a['point_b_glyph']} {a['point_b_name']}", a["formatted_orb"],
                         "→" if a.get("is_applying") else "←"] for a in c["aspects"]])
    eq = c["element_quality"]
    html += (f"<h2>{tr('Elemente & Qualitäten')}</h2><p>{tr('Feuer')} {eq['fire']} · {tr('Erde')} {eq['earth']} · {tr('Luft')} {eq['air']} · "
             f"{tr('Wasser')} {eq['water']} — {tr('Kardinal')} {eq['cardinal']} · {tr('Fix')} {eq['fixed']} · {tr('Veränderlich')} {eq['mutable']}</p>")

    html += f"<h2>{tr('Regel-Deutung')}</h2>"
    for sec in c.get("interpretations", []):
        html += f"<h3>{esc(sec['title'])}</h3><div class='muted'>{esc(sec['subtitle'])}</div><p>{esc(sec['text'])}</p>"

    for title, body in sections:
        html += f"<h2>{esc(title)}</h2>{body}"

    if ai_markdown:
        doc = QTextDocument()
        doc.setMarkdown(ai_markdown)
        inner = doc.toHtml()
        # nur den Body-Inhalt übernehmen
        start, end = inner.find("<body"), inner.rfind("</body>")
        if start >= 0 and end > start:
            inner = inner[inner.find(">", start) + 1:end]
        html += f"<h2>{tr('KI-Deutung')}</h2>{inner}"
    html += "</body></html>"
    return html


def export_pdf(path, html, title="Astrorust"):
    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(16, 16, 16, 16), QPageLayout.Unit.Millimeter)
    writer.setTitle(title)
    writer.setCreator("Astrorust")
    doc = QTextDocument()
    doc.setHtml(html)
    doc.print(writer)
