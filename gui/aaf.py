# -*- coding: utf-8 -*-
"""AAF'97 birth-data exchange; see DATA_SOURCES.md for the specification.

Calculated positions are deliberately recomputed. Unknown dates, missing
coordinates and unresolved time zones are rejected rather than guessed.
"""
import json
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo


def _angle(text, positive, negative):
    value = text.strip().lower()
    m = re.fullmatch(r'(\d+)(?:h?([' + positive + negative + r']))?(\d{0,2})(?::(\d{1,2}(?:\.\d+)?))?', value)
    if not m:
        if value in ('0h', '0:00', '0'):
            return 0.0
        raise ValueError(f'Ungültiger AAF-Winkel/Offset: {text}')
    degrees, direction, minutes, seconds = m.groups()
    if direction is None and value not in ('0',):
        raise ValueError(f'AAF-Richtung fehlt: {text}')
    minutes, seconds = float(minutes or 0), float(seconds or 0)
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f'Ungültige AAF-Minuten/Sekunden: {text}')
    result = int(degrees) + minutes / 60 + seconds / 3600
    return -result if direction == negative else result


def _format_angle(value, positive, negative, hours=False):
    total = round(abs(value) * 3600, 3)
    direction = positive if value >= 0 else negative
    return f'{int(total // 3600)}{"h" if hours else ""}{direction}{int(total // 60 % 60):02d}:{total % 60:06.3f}'


def loads(text, backend):
    records, chunks, key = [], {}, None
    for line in text.splitlines():
        if line.startswith('#') and ':' in line:
            tag, value = line[1:].split(':', 1)
            if tag == 'A93':
                if chunks:
                    records.append(chunks)
                chunks = {}
            key = tag
            if chunks or tag == 'A93':
                chunks[tag] = value.strip()
        elif chunks and key == 'COM':
            chunks['COM'] += '\n' + line
    if chunks:
        records.append(chunks)
    if not records:
        raise ValueError('Keine AAF-Datensätze (#A93) gefunden.')
    out = []
    for index, chunks in enumerate(records, 1):
        try:
            a = [v.strip() for v in chunks['A93'].split(',')]
            b = [v.strip() for v in chunks['B93'].split(',')]
            if len(a) != 7 or len(b) != 5:
                raise ValueError('#A93 braucht sieben, #B93 fünf Felder.')
            name = ' '.join(v for v in (a[1], a[0]) if v and v != '*')
            lat, lon = _angle(b[1], 'n', 's'), _angle(b[2], 'e', 'w')
            kind = b[4]
            if kind == 'L':
                offset = lon / 15.0
            elif kind in ('0', '1', '2', 'w', 'h', 'm'):
                offset = _angle(b[3], 'e', 'w') + {'1': 1, '2': 2, 'w': 1, 'h': 0.5}.get(kind, 0)
            elif b[0] != '*':
                # The Julian day takes precedence even if the time type is unknown.
                offset = _angle(b[3], 'e', 'w') if b[3] != '*' else 0.0
            else:
                raise ValueError(f'Unbekannter Zeittyp: {kind}')
            p = {'name': name, 'latitude': lat, 'longitude': lon, 'timezone': None,
                 'timezone_offset': offset, 'location_name': ', '.join(v for v in a[5:7] if v and v != '*'),
                 'notes': chunks.get('COM', ''), 'house_system': 'Placidus'}
            if b[0] != '*':
                jd = float(b[0])
                if not math.isfinite(jd):
                    raise ValueError('Ungültiger Julianischer Tag.')
                p.update(backend.call('calendar_date', {'jd': jd + offset / 24}))
            else:
                date = re.fullmatch(r'(\d{1,2})\.(\d{1,2})\.(-?\d+)([gj]?)', a[3])
                clock = re.fullmatch(r'(\d{1,2})(?:[:h](\d{0,2}))?(?::(\d{1,2}))?', a[4])
                if not date or not clock:
                    raise ValueError('Datum oder Geburtszeit fehlt oder ist ungültig.')
                day, month, year, calendar = date.groups()
                year, month, day = int(year), int(month), int(day)
                before_reform = (year, month, day) < (1582, 10, 15)
                if (calendar == 'g' and before_reform) or (calendar == 'j' and not before_reform):
                    raise ValueError('Abweichender Kalender benötigt einen #B93-Julianischen Tag.')
                p.update(year=year, month=month, day=day, hour=int(clock[1]),
                         minute=int(clock[2] or 0), second=int(clock[3] or 0))
            # Optional application metadata, never a substitute for the AAF time.
            if 'ASTRORUST' in chunks:
                meta = json.loads(chunks['ASTRORUST'])
                for field in ('group', 'tags', 'house_system', 'location_name'):
                    if field in meta:
                        p[field] = meta[field]
                zone = meta.get('timezone')
                if zone:
                    info = backend.call('resolve_timezone', {'zone': zone, 'year': p['year'], 'month': p['month'],
                        'day': p['day'], 'hour': p['hour'], 'minute': p['minute'], 'longitude': lon})
                    if abs(info['offset_hours'] - offset) < 1 / 3600:
                        p['timezone'] = zone
            out.append(p)
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f'AAF-Datensatz {index}: {e}') from e
    return out


def dumps(profiles, backend):
    output = ['#: Astrorust AAF97 birth data; positions are recomputed by the receiving application.']
    for p in profiles:
        chart = backend.call('chart', p)
        info = chart.get('timezone_info') or {}
        offset = info.get('offset_hours', p.get('timezone_offset', 0))
        kind, base = '0', offset
        if info.get('is_lmt'):
            kind = 'L'
        elif p.get('timezone'):
            d = datetime(p['year'], p['month'], p['day'], p.get('hour', 12), p.get('minute', 0), tzinfo=ZoneInfo(p['timezone']))
            dst = d.dst().total_seconds() / 3600 if d.dst() else 0
            code = {0: '0', 0.5: 'h', 1: '1', 2: '2'}.get(dst)
            if code is not None:
                kind, base = code, offset - dst
        def field(value):
            return str(value).replace(',', ';').replace('\n', ' ').replace('\r', ' ')
        date = f"{p['day']}.{p['month']}.{p['year']}"
        clock = f"{p.get('hour', 12):02d}:{p.get('minute', 0):02d}:{p.get('second', 0):02d}"
        place, _, country = (p.get('location_name') or '').rpartition(',')
        if not place:
            place, country = country, '*'
        output.append(f"#A93:{field(p['name'])},,e,{date},{clock},{field(place)},{field(country.strip())}")
        off = '*' if kind == 'L' else _format_angle(base, 'e', 'w', hours=True)
        output.append(f"#B93:{chart['julian_day']:.9f},{_format_angle(p['latitude'], 'n', 's')},{_format_angle(p['longitude'], 'e', 'w')},{off},{kind}")
        output.append('#ZNAM:' + field(info.get('abbreviation') or 'UTC'))
        if p.get('notes'):
            output.append('#COM:' + p['notes'])
        meta = {k: p[k] for k in ('group', 'tags', 'timezone', 'house_system', 'location_name') if k in p}
        output.append('#ASTRORUST:' + json.dumps(meta, ensure_ascii=False))
    return '\n'.join(output) + '\n'
