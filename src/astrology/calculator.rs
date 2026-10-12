use crate::astrology::analysis;
use crate::astrology::aspects::calculate_aspects_with;
use crate::astrology::chiron::chiron_position;
use crate::astrology::dignities::calculate_dignity;
use crate::astrology::engine;
use crate::astrology::interpretations::generate_interpretations;
use crate::astrology::models::{
    AnglesData, CelestialPoint, ChartRequest, ChartResponse, ChartSettings, Element, ElementQualitySummary,
    HouseCuspData, HouseSystemChoice, LilithType, NodeType, PlanetData, Quality, ZodiacSign, Zodiac,
};
use crate::astrology::tz::{self, TzInfo};
use crate::astrology::util::{
    days_to_epoch_secs, format_utc_offset, julian_day_ut, split_dm, split_dms, validate_request,
};

fn format_angle(sign: ZodiacSign, sign_deg: f64) -> String {
    let (d, m) = split_dm(sign_deg);
    format!("{} {:02}° {:02}'", sign.glyph(), d, m)
}

/// Alles, was zur Berechnung eines Horoskops für einen festen Zeitpunkt nötig ist.
pub struct ChartInput<'a> {
    pub name: String,
    pub jd_ut: f64,
    pub latitude: f64,
    pub longitude: f64,
    pub house_system: HouseSystemChoice,
    pub settings: &'a ChartSettings,
    pub date_time_label: String,
    pub location_name: String,
    pub timezone_info: Option<TzInfo>,
}

/// Zeitzone + Ortszeit → UTC-Offset (mit Sommerzeit, LMT-Korrektur auf den Ort).
pub fn resolve_zone(zone: &str, year: i32, month: i32, day: i32, local_hour: f64, longitude: f64) -> Result<TzInfo, String> {
    let jd_local = julian_day_ut(year, month, day, local_hour);
    let local_secs = days_to_epoch_secs(jd_local);
    let mut info = tz::resolve_local(zone, local_secs)?;
    if info.is_lmt {
        // Vor der Zonenzeit gilt die mittlere Ortszeit des Geburtsortes, nicht die der Zonenstadt.
        info.offset_hours = longitude / 15.0;
        info.note = format!(
            "Mittlere Ortszeit (LMT) des Ortes, {} – vor Einführung der Zonenzeit",
            format_utc_offset(info.offset_hours)
        );
    }
    Ok(info)
}

/// Löst Datum/Uhrzeit/Zone einer Anfrage zu JD (UT), Offset und Zeitzoneninfo auf.
pub fn resolve_time(req: &ChartRequest) -> Result<(f64, f64, Option<TzInfo>), String> {
    validate_request(req)?;
    let local_hour = req.hour as f64 + req.minute as f64 / 60.0 + req.second.unwrap_or(0) as f64 / 3600.0;

    let zone = req.timezone.as_deref().map(str::trim).filter(|z| !z.is_empty());
    let (offset, info) = match zone {
        Some(z) => {
            let info = resolve_zone(z, req.year, req.month, req.day, local_hour, req.longitude)?;
            (info.offset_hours, Some(info))
        }
        None => (req.timezone_offset, None),
    };
    let jd = julian_day_ut(req.year, req.month, req.day, local_hour - offset);
    Ok((jd, offset, info))
}

pub fn calculate_chart(req: &ChartRequest) -> Result<ChartResponse, String> {
    let (jd_ut, offset, info) = resolve_time(req)?;
    let settings = req.settings.clone().unwrap_or_default();

    let date_time_str = format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ({})",
        req.year,
        req.month,
        req.day,
        req.hour,
        req.minute,
        format_utc_offset(offset)
    );

    build_chart(&ChartInput {
        name: req.name.clone(),
        jd_ut,
        latitude: req.latitude,
        longitude: req.longitude,
        house_system: req.house_system.unwrap_or(HouseSystemChoice::Placidus),
        settings: &settings,
        date_time_label: date_time_str,
        location_name: req
            .location_name
            .clone()
            .filter(|s| !s.trim().is_empty())
            .unwrap_or_else(|| format!("{:.2}°, {:.2}°", req.latitude, req.longitude)),
        timezone_info: info,
    })
}

/// Rohposition eines Punktes.
#[derive(Debug, Clone, Copy)]
pub struct RawPos {
    pub lon: f64,
    pub lat: f64,
    pub dist: f64,
    pub speed: f64,
    pub retro: bool,
    pub files: bool,
}

pub fn position_flags(settings: &ChartSettings) -> sweph::Flags {
    let mut flags = sweph::Flags::SWISS;
    if settings.zodiac == Zodiac::Sidereal {
        flags |= sweph::Flags::SIDEREAL;
    }
    if settings.topocentric {
        flags |= sweph::Flags::TOPOCENTRIC;
    }
    flags
}

/// Position eines Punktes zu einem Zeitpunkt. Der Aufrufer hält die Engine-Sperre und hat
/// bei siderischer Rechnung den Modus gesetzt.
pub fn point_position(pt: CelestialPoint, jd_ut: f64, settings: &ChartSettings) -> Result<RawPos, String> {
    let sidereal = settings.zodiac == Zodiac::Sidereal;
    let body = match pt {
        CelestialPoint::TrueNode | CelestialPoint::SouthNode => match settings.node {
            NodeType::True => sweph::Body::TrueNode,
            NodeType::Mean => sweph::Body::MeanNode,
        },
        CelestialPoint::Lilith => match settings.lilith {
            LilithType::Mean => sweph::Body::MeanApogee,
            LilithType::Osculating => sweph::Body::OsculatingApogee,
        },
        CelestialPoint::Ascendant | CelestialPoint::Midheaven => {
            return Err("Achsen haben keine Planetenposition".into());
        }
        other => other.sweph_body(),
    };
    let raw = sweph::calc_with(jd_ut, body, position_flags(settings));
    let mut p = match raw {
        Ok(pos) => RawPos {
            lon: pos.longitude.rem_euclid(360.0),
            lat: pos.latitude,
            dist: pos.distance,
            speed: pos.speed_longitude,
            retro: pos.retrograde(),
            files: pos.ephemeris == sweph::Ephemeris::Swiss,
        },
        // Ohne seas_18.se1 kennt die Swiss Ephemeris Chiron nicht.
        Err(_) if pt == CelestialPoint::Chiron => {
            let (mut l, b, d, s, r) =
                chiron_position(jd_ut).ok_or_else(|| "Fehler bei Planetenberechnung Chiron".to_string())?;
            if sidereal {
                let ay = engine::ayanamsa_value(jd_ut, settings.ayanamsa).unwrap_or(0.0);
                l = (l - ay).rem_euclid(360.0);
            }
            RawPos { lon: l, lat: b, dist: d, speed: s, retro: r, files: false }
        }
        Err(e) => return Err(format!("Fehler bei Planetenberechnung {}: {:?}", pt.name_de(), e)),
    };
    if pt == CelestialPoint::SouthNode {
        p.lon = (p.lon + 180.0).rem_euclid(360.0);
    }
    Ok(p)
}

/// Horoskop für einen festen Zeitpunkt (UT) und Ort.
pub fn build_chart(input: &ChartInput) -> Result<ChartResponse, String> {
    let _engine = engine::lock();
    let settings = input.settings;
    let sidereal = settings.zodiac == Zodiac::Sidereal;
    let jd_ut = input.jd_ut;

    let mut house_flags = sweph::Flags::NONE;
    let mut ayanamsa_value = None;
    let mut ayanamsa_name = None;
    if sidereal {
        engine::set_sidereal(settings.ayanamsa);
        house_flags |= sweph::Flags::SIDEREAL;
        ayanamsa_value = engine::ayanamsa_value(jd_ut, settings.ayanamsa).ok();
        ayanamsa_name = engine::AYANAMSAS.iter().find(|(id, _)| *id == settings.ayanamsa).map(|(_, n)| n.to_string());
        // ayanamsa_value() setzt den Modus erneut – gleiche ID, daher unkritisch
    }
    if settings.topocentric {
        sweph::set_topocentric(input.longitude, input.latitude, 0.0);
    }

    // Häuser & Achsen. Quadrantensysteme sind innerhalb der Polarkreise nicht definiert;
    // dann wird auf Porphyrius ausgewichen.
    let requested_system = input.house_system;
    let mut house_system_label = requested_system.name_de().to_string();
    let houses_calc = match sweph::houses_with(jd_ut, input.latitude, input.longitude, requested_system.to_sweph(), house_flags) {
        Ok(h) => h,
        Err(first_err) => {
            let fallback = HouseSystemChoice::Porphyry;
            match sweph::houses_with(jd_ut, input.latitude, input.longitude, fallback.to_sweph(), house_flags) {
                Ok(h) => {
                    house_system_label = format!(
                        "{} (Ersatz für {}: am Polarkreis nicht definiert)",
                        fallback.name_de(),
                        requested_system.name_de()
                    );
                    h
                }
                Err(_) => return Err(format!("Fehler bei Häuserberechnung: {:?}", first_err)),
            }
        }
    };

    let mut house_cusps = Vec::with_capacity(12);
    for i in 0..12 {
        let cusp_deg = houses_calc.cusps[i].rem_euclid(360.0);
        let (sign, sign_deg) = ZodiacSign::from_degrees(cusp_deg);
        let (deg_int, min_int) = split_dm(sign_deg);
        house_cusps.push(HouseCuspData {
            house_number: (i + 1) as u8,
            longitude: cusp_deg,
            sign,
            sign_name: sign.name_de().to_string(),
            sign_glyph: sign.glyph().to_string(),
            deg_int,
            min_int,
            formatted_deg: format!("{:02}° {:02}'", deg_int, min_int),
        });
    }

    // Planeten
    let mut points: Vec<PointPos> = Vec::new();
    let mut files_used = false;
    for pt in settings.points() {
        let pos = point_position(pt, jd_ut, settings)?;
        files_used |= pos.files;

        // Deklination (tropisch-äquatorial)
        let decl = if pt == CelestialPoint::Chiron && !pos.files {
            0.0
        } else {
            let body = match pt {
                CelestialPoint::TrueNode | CelestialPoint::SouthNode => match settings.node {
                    NodeType::True => sweph::Body::TrueNode,
                    NodeType::Mean => sweph::Body::MeanNode,
                },
                CelestialPoint::Lilith => match settings.lilith {
                    LilithType::Mean => sweph::Body::MeanApogee,
                    LilithType::Osculating => sweph::Body::OsculatingApogee,
                },
                other => other.sweph_body(),
            };
            sweph::calc_with(jd_ut, body, sweph::Flags::SWISS | sweph::Flags::EQUATORIAL | if settings.topocentric { sweph::Flags::TOPOCENTRIC } else { sweph::Flags::NONE })
                .map(|p| p.latitude)
                .unwrap_or(0.0)
        };
        let decl = if pt == CelestialPoint::SouthNode { -decl } else { decl };
        points.push(PointPos { id: pt, lon: pos.lon, lat: pos.lat, dist: pos.dist, speed: pos.speed, retro: pos.retro, decl });
    }

    let houses = HouseSet {
        cusps: houses_calc.cusps,
        ascendant: houses_calc.ascendant,
        midheaven: houses_calc.midheaven,
        vertex: houses_calc.vertex,
    };
    let meta = ChartMeta {
        name: input.name.clone(),
        date_time: input.date_time_label.clone(),
        location_name: input.location_name.clone(),
        latitude: input.latitude,
        longitude: input.longitude,
        julian_day: jd_ut,
        house_system_label,
        timezone_info: input.timezone_info.clone(),
        ayanamsa_name,
        ayanamsa_value,
        ephemeris_files: files_used,
    };
    Ok(assemble_chart(&meta, points, &houses, settings))
}

/// Häuser und Achsen eines Horoskops.
#[derive(Debug, Clone, Copy)]
pub struct HouseSet {
    pub cusps: [f64; 12],
    pub ascendant: f64,
    pub midheaven: f64,
    pub vertex: f64,
}

/// Roh-Position eines Punktes für `assemble_chart`.
#[derive(Debug, Clone, Copy)]
pub struct PointPos {
    pub id: CelestialPoint,
    pub lon: f64,
    pub lat: f64,
    pub dist: f64,
    pub speed: f64,
    pub retro: bool,
    pub decl: f64,
}

pub struct ChartMeta {
    pub name: String,
    pub date_time: String,
    pub location_name: String,
    pub latitude: f64,
    pub longitude: f64,
    pub julian_day: f64,
    pub house_system_label: String,
    pub timezone_info: Option<TzInfo>,
    pub ayanamsa_name: Option<String>,
    pub ayanamsa_value: Option<f64>,
    pub ephemeris_files: bool,
}

/// Baut aus Positionen und Häusern die komplette Antwort (Zeichen, Häuser, Aspekte,
/// Elemente, Deutungen, Analysen). Wird auch für Composite, Solarbogen usw. genutzt.
pub fn assemble_chart(meta: &ChartMeta, points: Vec<PointPos>, houses_calc: &HouseSet, settings: &ChartSettings) -> ChartResponse {
    let mut house_cusps = Vec::with_capacity(12);
    for i in 0..12 {
        let cusp_deg = houses_calc.cusps[i].rem_euclid(360.0);
        let (sign, sign_deg) = ZodiacSign::from_degrees(cusp_deg);
        let (deg_int, min_int) = split_dm(sign_deg);
        house_cusps.push(HouseCuspData {
            house_number: (i + 1) as u8,
            longitude: cusp_deg,
            sign,
            sign_name: sign.name_de().to_string(),
            sign_glyph: sign.glyph().to_string(),
            deg_int,
            min_int,
            formatted_deg: format!("{:02}° {:02}'", deg_int, min_int),
        });
    }

    let mut planets: Vec<PlanetData> = Vec::new();
    for pp in &points {
        let pt = pp.id;
        let lon = pp.lon.rem_euclid(360.0);
        let (sign, sign_deg) = ZodiacSign::from_degrees(lon);
        let (deg_int, min_int, sec_int) = split_dms(sign_deg);
        let house_num = determine_house(lon, &houses_calc.cusps);
        let dignity = calculate_dignity(pt, sign);

        let mut display_name = pt.name_de().to_string();
        match pt {
            CelestialPoint::TrueNode if settings.node == NodeType::Mean => display_name = "Mondknoten (mittel)".into(),
            CelestialPoint::SouthNode if settings.node == NodeType::Mean => display_name = "Südknoten (mittel)".into(),
            CelestialPoint::Lilith if settings.lilith == LilithType::Osculating => display_name = "Lilith (oskulierend)".into(),
            _ => {}
        }

        planets.push(PlanetData {
            id: pt,
            name: display_name,
            glyph: pt.glyph().to_string(),
            longitude: lon,
            latitude: pp.lat,
            distance: pp.dist,
            speed: pp.speed,
            is_retrograde: pp.retro,
            sign,
            sign_name: sign.name_de().to_string(),
            sign_glyph: sign.glyph().to_string(),
            sign_deg,
            deg_int,
            min_int,
            sec_int,
            formatted_deg: format!("{:02}° {:02}' {:02}\"", deg_int, min_int, sec_int),
            house: house_num,
            dignity,
            declination: pp.decl,
        });
    }

    // Achsen und Sonderpunkte
    let asc_deg = houses_calc.ascendant.rem_euclid(360.0);
    let (asc_sign, asc_sign_deg) = ZodiacSign::from_degrees(asc_deg);
    let mc_deg = houses_calc.midheaven.rem_euclid(360.0);
    let (mc_sign, mc_sign_deg) = ZodiacSign::from_degrees(mc_deg);
    let desc_deg = (asc_deg + 180.0).rem_euclid(360.0);
    let (desc_sign, desc_sign_deg) = ZodiacSign::from_degrees(desc_deg);
    let ic_deg = (mc_deg + 180.0).rem_euclid(360.0);
    let (ic_sign, ic_sign_deg) = ZodiacSign::from_degrees(ic_deg);
    let vtx_deg = houses_calc.vertex.rem_euclid(360.0);
    let (vtx_sign, vtx_sign_deg) = ZodiacSign::from_degrees(vtx_deg);

    let lon_of = |id: CelestialPoint| planets.iter().find(|p| p.id == id).map(|p| p.longitude).unwrap_or(0.0);
    let sun_lon = lon_of(CelestialPoint::Sun);
    let moon_lon = lon_of(CelestialPoint::Moon);

    // Tageshoroskop: Sonne über dem Horizont (180°–360° vom AC aus) – unabhängig vom Häusersystem.
    let is_diurnal = (sun_lon - asc_deg).rem_euclid(360.0) >= 180.0;
    let fortune_deg = if is_diurnal {
        (asc_deg + moon_lon - sun_lon).rem_euclid(360.0)
    } else {
        (asc_deg + sun_lon - moon_lon).rem_euclid(360.0)
    };
    let (fort_sign, fort_sign_deg) = ZodiacSign::from_degrees(fortune_deg);

    let angles = AnglesData {
        ascendant: asc_deg,
        ascendant_sign: asc_sign,
        ascendant_formatted: format_angle(asc_sign, asc_sign_deg),
        midheaven: mc_deg,
        midheaven_sign: mc_sign,
        midheaven_formatted: format_angle(mc_sign, mc_sign_deg),
        descendant: desc_deg,
        descendant_formatted: format_angle(desc_sign, desc_sign_deg),
        imum_coeli: ic_deg,
        imum_coeli_formatted: format_angle(ic_sign, ic_sign_deg),
        part_of_fortune: fortune_deg,
        part_of_fortune_formatted: format_angle(fort_sign, fort_sign_deg),
        vertex: vtx_deg,
        vertex_formatted: format_angle(vtx_sign, vtx_sign_deg),
    };

    let aspects = calculate_aspects_with(&planets, settings);

    // Elemente und Qualitäten: die zehn klassischen Planeten plus Aszendent.
    let (mut fire, mut earth, mut air, mut water) = (0, 0, 0, 0);
    let (mut cardinal, mut fixed, mut mutable) = (0, 0, 0);
    let counted_signs = planets
        .iter()
        .filter(|p| !p.id.is_sensitive_point())
        .map(|p| p.sign)
        .chain(std::iter::once(asc_sign));
    for sign in counted_signs {
        match sign.element() {
            Element::Fire => fire += 1,
            Element::Earth => earth += 1,
            Element::Air => air += 1,
            Element::Water => water += 1,
        }
        match sign.quality() {
            Quality::Cardinal => cardinal += 1,
            Quality::Fixed => fixed += 1,
            Quality::Mutable => mutable += 1,
        }
    }
    let dominant_element = {
        let mut max_e = ("Feuer", fire);
        if earth > max_e.1 {
            max_e = ("Erde", earth);
        }
        if air > max_e.1 {
            max_e = ("Luft", air);
        }
        if water > max_e.1 {
            max_e = ("Wasser", water);
        }
        max_e.0.to_string()
    };
    let dominant_quality = {
        let mut max_q = ("Kardinal", cardinal);
        if fixed > max_q.1 {
            max_q = ("Fix", fixed);
        }
        if mutable > max_q.1 {
            max_q = ("Veränderlich", mutable);
        }
        max_q.0.to_string()
    };
    let element_quality = ElementQualitySummary { fire, earth, air, water, cardinal, fixed, mutable, dominant_element, dominant_quality };

    let interpretations = generate_interpretations(&planets, asc_sign, &aspects, &element_quality);

    let mut chart = ChartResponse {
        name: meta.name.clone(),
        date_time: meta.date_time.clone(),
        location_name: meta.location_name.clone(),
        latitude: meta.latitude,
        longitude: meta.longitude,
        julian_day: meta.julian_day,
        house_system: meta.house_system_label.clone(),
        planets,
        houses: house_cusps,
        angles,
        aspects,
        element_quality,
        interpretations,
        timezone_info: meta.timezone_info.clone(),
        analysis: None,
        zodiac: settings.zodiac,
        ayanamsa_name: meta.ayanamsa_name.clone(),
        ayanamsa_value: meta.ayanamsa_value,
        is_diurnal,
        ephemeris_files: meta.ephemeris_files,
    };
    if settings.analysis {
        chart.analysis = Some(analysis::analyze(&chart, settings));
    }
    chart
}

pub fn determine_house(lon: f64, cusps: &[f64; 12]) -> u8 {
    for i in 0..12 {
        let current_cusp = cusps[i].rem_euclid(360.0);
        let next_cusp = cusps[(i + 1) % 12].rem_euclid(360.0);
        let house_width = (next_cusp - current_cusp).rem_euclid(360.0);
        let dist = (lon - current_cusp).rem_euclid(360.0);
        if dist < house_width {
            return (i + 1) as u8;
        }
    }
    1
}
