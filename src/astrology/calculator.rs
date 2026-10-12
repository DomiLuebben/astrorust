use crate::astrology::aspects::calculate_aspects;
use crate::astrology::chiron::chiron_position;
use crate::astrology::dignities::calculate_dignity;
use crate::astrology::interpretations::generate_interpretations;
use crate::astrology::models::{
    AnglesData, CelestialPoint, ChartRequest, ChartResponse, Element, ElementQualitySummary,
    HouseCuspData, HouseSystemChoice, PlanetData, Quality, ZodiacSign,
};
use crate::astrology::util::{
    format_utc_offset, julian_day_ut, split_dm, split_dms, validate_request,
};
use std::sync::Once;

static EPHE_INIT: Once = Once::new();

/// Sucht Swiss-Ephemeris-Dateien (`*.se1`) und meldet den Pfad an die C-Bibliothek.
/// Ohne Dateien rechnet die Bibliothek mit Moshier (für Chiron greift `chiron.rs`).
fn init_ephemeris() {
    EPHE_INIT.call_once(|| {
        let mut candidates: Vec<String> = Vec::new();
        if let Ok(p) = std::env::var("ASTRORUST_EPHE") {
            candidates.push(p);
        }
        if let Ok(home) = std::env::var("HOME") {
            candidates.push(format!("{}/.local/share/astrorust/ephe", home));
        }
        candidates.push("/usr/share/astrorust/ephe".into());
        candidates.push("/usr/share/swisseph".into());
        candidates.push("/usr/share/sweph/ephe".into());
        for dir in candidates {
            let has_files = std::fs::read_dir(&dir)
                .map(|rd| {
                    rd.flatten()
                        .any(|e| e.path().extension().map_or(false, |x| x == "se1"))
                })
                .unwrap_or(false);
            if has_files && !dir.contains('\0') {
                sweph::set_ephe_path(&dir);
                break;
            }
        }
    });
}

fn format_angle(sign: ZodiacSign, sign_deg: f64) -> String {
    let (d, m) = split_dm(sign_deg);
    format!("{} {:02}° {:02}'", sign.glyph(), d, m)
}

pub fn calculate_chart(req: &ChartRequest) -> Result<ChartResponse, String> {
    validate_request(req)?;
    init_ephemeris();

    // 1. Julianischer Tag (UT)
    let dec_hour = req.hour as f64
        + (req.minute as f64 / 60.0)
        + (req.second.unwrap_or(0) as f64 / 3600.0);
    let ut_hour = dec_hour - req.timezone_offset;
    let jd_ut = julian_day_ut(req.year, req.month, req.day, ut_hour);

    // 2. Häuser & Achsen. Quadrantensysteme sind innerhalb der Polarkreise nicht
    //    definiert; dann wird – wie in gängiger Software – auf Porphyrius ausgewichen.
    let requested_system = req.house_system.unwrap_or(HouseSystemChoice::Placidus);
    let mut house_system_label = requested_system.name_de().to_string();
    let houses_calc = match sweph::houses(
        jd_ut,
        req.latitude,
        req.longitude,
        requested_system.to_sweph(),
    ) {
        Ok(h) => h,
        Err(first_err) => {
            let fallback = HouseSystemChoice::Porphyry;
            match sweph::houses(jd_ut, req.latitude, req.longitude, fallback.to_sweph()) {
                Ok(h) => {
                    house_system_label = format!(
                        "{} (Ersatz für {}: am Polarkreis nicht definiert)",
                        fallback.name_de(),
                        requested_system.name_de()
                    );
                    h
                }
                Err(_) => {
                    return Err(format!("Fehler bei Häuserberechnung: {:?}", first_err));
                }
            }
        }
    };

    // 3. Häuserspitzen
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

    // 4. Planeten
    let mut planets = Vec::new();
    for &pt in CelestialPoint::all() {
        let (lon, lat, dist, speed, is_retro) = match sweph::calc(jd_ut, pt.sweph_body()) {
            Ok(pos) => (
                pos.longitude.rem_euclid(360.0),
                pos.latitude,
                pos.distance,
                pos.speed_longitude,
                pos.retrograde(),
            ),
            // Ohne seas_18.se1 kennt die Swiss Ephemeris Chiron nicht.
            Err(_) if pt == CelestialPoint::Chiron => chiron_position(jd_ut)
                .ok_or_else(|| "Fehler bei Planetenberechnung Chiron".to_string())?,
            Err(e) => {
                return Err(format!(
                    "Fehler bei Planetenberechnung {}: {:?}",
                    pt.name_de(),
                    e
                ));
            }
        };

        let (sign, sign_deg) = ZodiacSign::from_degrees(lon);
        let (deg_int, min_int, sec_int) = split_dms(sign_deg);

        let house_num = determine_house(lon, &houses_calc.cusps);
        let dignity = calculate_dignity(pt, sign);

        planets.push(PlanetData {
            id: pt,
            name: pt.name_de().to_string(),
            glyph: pt.glyph().to_string(),
            longitude: lon,
            latitude: lat,
            distance: dist,
            speed,
            is_retrograde: is_retro,
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
        });
    }

    // 5. Achsen und Sonderpunkte
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

    // Glückspunkt (Pars Fortunae)
    let sun_lon = planets
        .iter()
        .find(|p| p.id == CelestialPoint::Sun)
        .map(|p| p.longitude)
        .unwrap_or(0.0);
    let moon_lon = planets
        .iter()
        .find(|p| p.id == CelestialPoint::Moon)
        .map(|p| p.longitude)
        .unwrap_or(0.0);

    // Tageshoroskop: Sonne über dem Horizont, also zwischen DC und AC gegen den
    // Uhrzeigersinn (180°–360° vom AC aus). Unabhängig vom Häusersystem.
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

    // 6. Aspekte
    let aspects = calculate_aspects(&planets);

    // 7. Elemente und Qualitäten: die zehn klassischen Planeten plus Aszendent.
    //    Mondknoten, Chiron und Lilith sind Empfindlichkeitspunkte und zählen nicht mit.
    let (mut fire, mut earth, mut air, mut water) = (0, 0, 0, 0);
    let (mut cardinal, mut fixed, mut mutable) = (0, 0, 0);

    let counted_signs = planets
        .iter()
        .filter(|p| {
            !matches!(
                p.id,
                CelestialPoint::TrueNode | CelestialPoint::Chiron | CelestialPoint::Lilith
            )
        })
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

    let element_quality = ElementQualitySummary {
        fire,
        earth,
        air,
        water,
        cardinal,
        fixed,
        mutable,
        dominant_element,
        dominant_quality,
    };

    // 8. Deutungen
    let interpretations = generate_interpretations(&planets, asc_sign, &aspects, &element_quality);

    let date_time_str = format!(
        "{:04}-{:02}-{:02} {:02}:{:02} ({})",
        req.year,
        req.month,
        req.day,
        req.hour,
        req.minute,
        format_utc_offset(req.timezone_offset)
    );

    Ok(ChartResponse {
        name: req.name.clone(),
        date_time: date_time_str,
        location_name: req
            .location_name
            .clone()
            .filter(|s| !s.trim().is_empty())
            .unwrap_or_else(|| format!("{:.2}°, {:.2}°", req.latitude, req.longitude)),
        latitude: req.latitude,
        longitude: req.longitude,
        julian_day: jd_ut,
        house_system: house_system_label,
        planets,
        houses: house_cusps,
        angles,
        aspects,
        element_quality,
        interpretations,
    })
}

fn determine_house(lon: f64, cusps: &[f64; 12]) -> u8 {
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
