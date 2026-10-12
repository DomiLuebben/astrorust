use crate::astrology::aspects::calculate_aspects;
use crate::astrology::dignities::calculate_dignity;
use crate::astrology::interpretations::generate_interpretations;
use crate::astrology::models::{
    AnglesData, ChartRequest, ChartResponse, Element, ElementQualitySummary, HouseCuspData,
    HouseSystemChoice, PlanetData, Quality, ZodiacSign,
};

pub fn calculate_chart(req: &ChartRequest) -> Result<ChartResponse, String> {
    // 1. Calculate Julian Day UT
    let dec_hour = req.hour as f64
        + (req.minute as f64 / 60.0)
        + (req.second.unwrap_or(0) as f64 / 3600.0);
    let ut_hour = dec_hour - req.timezone_offset;

    let jd_ut = sweph::julian_day(req.year, req.month, req.day, ut_hour);

    // 2. Calculate Houses & Angles
    let house_sys_choice = req.house_system.unwrap_or(HouseSystemChoice::Placidus);
    let houses_res = sweph::houses(
        jd_ut,
        req.latitude,
        req.longitude,
        house_sys_choice.to_sweph(),
    );

    let houses_calc = houses_res.map_err(|e| format!("Fehler bei Häuserberechnung: {:?}", e))?;

    // 3. Prepare Houses Data
    let mut house_cusps = Vec::with_capacity(12);
    for i in 0..12 {
        let cusp_deg = houses_calc.cusps[i].rem_euclid(360.0);
        let (sign, sign_deg) = ZodiacSign::from_degrees(cusp_deg);
        let deg_int = sign_deg.floor() as u32;
        let min_int = ((sign_deg - deg_int as f64) * 60.0).round() as u32;
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

    // 4. Calculate Planets
    let mut planets = Vec::new();
    for &pt in crate::astrology::models::CelestialPoint::all() {
        let pos_opt = sweph::calc(jd_ut, pt.sweph_body());

        let (lon, lat, dist, speed, is_retro) = match pos_opt {
            Ok(pos) => (
                pos.longitude.rem_euclid(360.0),
                pos.latitude,
                pos.distance,
                pos.speed_longitude,
                pos.retrograde(),
            ),
            Err(_) if pt == crate::astrology::models::CelestialPoint::Chiron => {
                // Compute Chiron via osculating Keplerian orbital elements
                let chiron_calc = calculate_chiron_kepler(jd_ut);
                (chiron_calc.0, chiron_calc.1, chiron_calc.2, chiron_calc.3, chiron_calc.4)
            }
            Err(e) => {
                return Err(format!(
                    "Fehler bei Planetenberechnung {}: {:?}",
                    pt.name_de(),
                    e
                ));
            }
        };

        let (sign, sign_deg) = ZodiacSign::from_degrees(lon);
        let deg_int = sign_deg.floor() as u32;
        let rem_min = (sign_deg - deg_int as f64) * 60.0;
        let min_int = rem_min.floor() as u32;
        let sec_int = ((rem_min - min_int as f64) * 60.0).round() as u32;

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

    // 5. Angles and Special Points
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

    // Part of Fortune
    let sun_pos = planets
        .iter()
        .find(|p| p.id == crate::astrology::models::CelestialPoint::Sun)
        .map(|p| (p.longitude, p.house))
        .unwrap_or((0.0, 1));
    let moon_pos = planets
        .iter()
        .find(|p| p.id == crate::astrology::models::CelestialPoint::Moon)
        .map(|p| p.longitude)
        .unwrap_or(0.0);

    // Diurnal if Sun is in houses 7..=12
    let is_diurnal = sun_pos.1 >= 7 && sun_pos.1 <= 12;
    let fortune_deg = if is_diurnal {
        (asc_deg + moon_pos - sun_pos.0).rem_euclid(360.0)
    } else {
        (asc_deg + sun_pos.0 - moon_pos).rem_euclid(360.0)
    };
    let (fort_sign, fort_sign_deg) = ZodiacSign::from_degrees(fortune_deg);

    let angles = AnglesData {
        ascendant: asc_deg,
        ascendant_sign: asc_sign,
        ascendant_formatted: format!(
            "{} {:02}° {:02}'",
            asc_sign.glyph(),
            asc_sign_deg.floor() as u32,
            ((asc_sign_deg - asc_sign_deg.floor()) * 60.0).round() as u32
        ),
        midheaven: mc_deg,
        midheaven_sign: mc_sign,
        midheaven_formatted: format!(
            "{} {:02}° {:02}'",
            mc_sign.glyph(),
            mc_sign_deg.floor() as u32,
            ((mc_sign_deg - mc_sign_deg.floor()) * 60.0).round() as u32
        ),
        descendant: desc_deg,
        descendant_formatted: format!(
            "{} {:02}° {:02}'",
            desc_sign.glyph(),
            desc_sign_deg.floor() as u32,
            ((desc_sign_deg - desc_sign_deg.floor()) * 60.0).round() as u32
        ),
        imum_coeli: ic_deg,
        imum_coeli_formatted: format!(
            "{} {:02}° {:02}'",
            ic_sign.glyph(),
            ic_sign_deg.floor() as u32,
            ((ic_sign_deg - ic_sign_deg.floor()) * 60.0).round() as u32
        ),
        part_of_fortune: fortune_deg,
        part_of_fortune_formatted: format!(
            "{} {:02}° {:02}'",
            fort_sign.glyph(),
            fort_sign_deg.floor() as u32,
            ((fort_sign_deg - fort_sign_deg.floor()) * 60.0).round() as u32
        ),
        vertex: vtx_deg,
        vertex_formatted: format!(
            "{} {:02}° {:02}'",
            vtx_sign.glyph(),
            vtx_sign_deg.floor() as u32,
            ((vtx_sign_deg - vtx_sign_deg.floor()) * 60.0).round() as u32
        ),
    };

    // 6. Aspects
    let aspects = calculate_aspects(&planets);

    // 7. Element and Quality summary
    let mut fire = 0;
    let mut earth = 0;
    let mut air = 0;
    let mut water = 0;
    let mut cardinal = 0;
    let mut fixed = 0;
    let mut mutable = 0;

    // Weight major planets and Ascendant
    for p in &planets {
        match p.sign.element() {
            Element::Fire => fire += 1,
            Element::Earth => earth += 1,
            Element::Air => air += 1,
            Element::Water => water += 1,
        }
        match p.sign.quality() {
            Quality::Cardinal => cardinal += 1,
            Quality::Fixed => fixed += 1,
            Quality::Mutable => mutable += 1,
        }
    }
    // Also include Ascendant sign
    match asc_sign.element() {
        Element::Fire => fire += 1,
        Element::Earth => earth += 1,
        Element::Air => air += 1,
        Element::Water => water += 1,
    }
    match asc_sign.quality() {
        Quality::Cardinal => cardinal += 1,
        Quality::Fixed => fixed += 1,
        Quality::Mutable => mutable += 1,
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

    // 8. Interpretations
    let interpretations = generate_interpretations(&planets, asc_sign, &aspects, &element_quality);

    let date_time_str = format!(
        "{:04}-{:02}-{:02} {:02}:{:02} (UTC{:+.1})",
        req.year, req.month, req.day, req.hour, req.minute, req.timezone_offset
    );

    Ok(ChartResponse {
        name: req.name.clone(),
        date_time: date_time_str,
        location_name: req
            .location_name
            .clone()
            .unwrap_or_else(|| format!("{:.2}°, {:.2}°", req.latitude, req.longitude)),
        latitude: req.latitude,
        longitude: req.longitude,
        julian_day: jd_ut,
        house_system: house_sys_choice.name_de().to_string(),
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

fn calculate_chiron_kepler(jd: f64) -> (f64, f64, f64, f64, bool) {
    let pos_a = chiron_raw_lon(jd);
    let pos_b = chiron_raw_lon(jd + 0.1);

    let mut d_lon = pos_b.0 - pos_a.0;
    if d_lon > 180.0 { d_lon -= 360.0; }
    if d_lon < -180.0 { d_lon += 360.0; }
    let speed = d_lon / 0.1;
    let is_retro = speed < 0.0;

    (pos_a.0, pos_a.1, pos_a.2, speed, is_retro)
}

fn chiron_raw_lon(jd: f64) -> (f64, f64, f64) {
    let d = jd - 2451545.0; // days from J2000.0
    let a = 13.670; // AU
    let e = 0.383;
    let inc = 6.94_f64.to_radians();
    let omega = 339.6_f64.to_radians();
    let big_omega = 209.3_f64.to_radians();

    let n = 0.019538_f64.to_radians(); // mean motion per day
    let m0 = 126.3_f64.to_radians();
    let m = (m0 + n * d).rem_euclid(std::f64::consts::TAU);

    // Solve Kepler's equation E - e*sin(E) = M
    let mut e_anom = m;
    for _ in 0..10 {
        let f = e_anom - e * e_anom.sin() - m;
        let f_prime = 1.0 - e * e_anom.cos();
        e_anom -= f / f_prime;
    }

    let nu = 2.0 * (((1.0 + e) / (1.0 - e)).sqrt() * (e_anom / 2.0).tan()).atan();
    let r = a * (1.0 - e * e_anom.cos());

    let u = nu + omega;
    let x_h = r * (big_omega.cos() * u.cos() - big_omega.sin() * u.sin() * inc.cos());
    let y_h = r * (big_omega.sin() * u.cos() + big_omega.cos() * u.sin() * inc.cos());
    let z_h = r * (u.sin() * inc.sin());

    // Approximate Sun's geocentric position
    let sun_pos = sweph::calc(jd, sweph::Body::Sun).ok();
    let (sun_x, sun_y) = if let Some(sp) = sun_pos {
        let sl = sp.longitude.to_radians();
        let sr = sp.distance;
        (sr * sl.cos(), sr * sl.sin())
    } else {
        let sun_lon = (280.460 + 0.9856474 * d).rem_euclid(360.0).to_radians();
        (sun_lon.cos(), sun_lon.sin())
    };

    let x_g = x_h + sun_x;
    let y_g = y_h + sun_y;
    let z_g = z_h;

    let dist = (x_g * x_g + y_g * y_g + z_g * z_g).sqrt();
    let lon = y_g.atan2(x_g).to_degrees().rem_euclid(360.0);
    let lat = (z_g / dist).asin().to_degrees();

    (lon, lat, dist)
}
