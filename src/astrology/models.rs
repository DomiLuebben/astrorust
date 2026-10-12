use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum CelestialPoint {
    Sun,
    Moon,
    Mercury,
    Venus,
    Mars,
    Jupiter,
    Saturn,
    Uranus,
    Neptune,
    Pluto,
    TrueNode,
    Chiron,
    Lilith,
}

impl CelestialPoint {
    pub fn all() -> &'static [CelestialPoint] {
        &[
            CelestialPoint::Sun,
            CelestialPoint::Moon,
            CelestialPoint::Mercury,
            CelestialPoint::Venus,
            CelestialPoint::Mars,
            CelestialPoint::Jupiter,
            CelestialPoint::Saturn,
            CelestialPoint::Uranus,
            CelestialPoint::Neptune,
            CelestialPoint::Pluto,
            CelestialPoint::TrueNode,
            CelestialPoint::Chiron,
            CelestialPoint::Lilith,
        ]
    }

    pub fn name_de(&self) -> &'static str {
        match self {
            CelestialPoint::Sun => "Sonne",
            CelestialPoint::Moon => "Mond",
            CelestialPoint::Mercury => "Merkur",
            CelestialPoint::Venus => "Venus",
            CelestialPoint::Mars => "Mars",
            CelestialPoint::Jupiter => "Jupiter",
            CelestialPoint::Saturn => "Saturn",
            CelestialPoint::Uranus => "Uranus",
            CelestialPoint::Neptune => "Neptun",
            CelestialPoint::Pluto => "Pluto",
            CelestialPoint::TrueNode => "Mondknoten",
            CelestialPoint::Chiron => "Chiron",
            CelestialPoint::Lilith => "Lilith",
        }
    }

    pub fn glyph(&self) -> &'static str {
        match self {
            CelestialPoint::Sun => "☉",
            CelestialPoint::Moon => "☽",
            CelestialPoint::Mercury => "☿",
            CelestialPoint::Venus => "♀",
            CelestialPoint::Mars => "♂",
            CelestialPoint::Jupiter => "♃",
            CelestialPoint::Saturn => "♄",
            CelestialPoint::Uranus => "♅",
            CelestialPoint::Neptune => "♆",
            CelestialPoint::Pluto => "♇",
            CelestialPoint::TrueNode => "☊",
            CelestialPoint::Chiron => "⚷",
            CelestialPoint::Lilith => "⚸",
        }
    }

    pub fn sweph_body(&self) -> sweph::Body {
        match self {
            CelestialPoint::Sun => sweph::Body::Sun,
            CelestialPoint::Moon => sweph::Body::Moon,
            CelestialPoint::Mercury => sweph::Body::Mercury,
            CelestialPoint::Venus => sweph::Body::Venus,
            CelestialPoint::Mars => sweph::Body::Mars,
            CelestialPoint::Jupiter => sweph::Body::Jupiter,
            CelestialPoint::Saturn => sweph::Body::Saturn,
            CelestialPoint::Uranus => sweph::Body::Uranus,
            CelestialPoint::Neptune => sweph::Body::Neptune,
            CelestialPoint::Pluto => sweph::Body::Pluto,
            CelestialPoint::TrueNode => sweph::Body::TrueNode,
            CelestialPoint::Chiron => sweph::Body::Chiron,
            CelestialPoint::Lilith => sweph::Body::MeanApogee,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Element {
    Fire,
    Earth,
    Air,
    Water,
}

#[allow(dead_code)]
impl Element {
    pub fn name_de(&self) -> &'static str {
        match self {
            Element::Fire => "Feuer",
            Element::Earth => "Erde",
            Element::Air => "Luft",
            Element::Water => "Wasser",
        }
    }

    pub fn color_hex(&self) -> &'static str {
        match self {
            Element::Fire => "#f87171",  // Warm Red/Coral
            Element::Earth => "#4ade80", // Forest Emerald
            Element::Air => "#fbbf24",   // Warm Gold/Amber
            Element::Water => "#60a5fa", // Ocean Azure
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Quality {
    Cardinal,
    Fixed,
    Mutable,
}

#[allow(dead_code)]
impl Quality {
    pub fn name_de(&self) -> &'static str {
        match self {
            Quality::Cardinal => "Kardinal",
            Quality::Fixed => "Fix",
            Quality::Mutable => "Veränderlich",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ZodiacSign {
    Aries = 0,
    Taurus = 1,
    Gemini = 2,
    Cancer = 3,
    Leo = 4,
    Virgo = 5,
    Libra = 6,
    Scorpio = 7,
    Sagittarius = 8,
    Capricorn = 9,
    Aquarius = 10,
    Pisces = 11,
}

impl ZodiacSign {
    pub fn from_degrees(degrees: f64) -> (ZodiacSign, f64) {
        let norm = degrees.rem_euclid(360.0);
        let sign_index = (norm / 30.0).floor() as usize;
        let sign = match sign_index.min(11) {
            0 => ZodiacSign::Aries,
            1 => ZodiacSign::Taurus,
            2 => ZodiacSign::Gemini,
            3 => ZodiacSign::Cancer,
            4 => ZodiacSign::Leo,
            5 => ZodiacSign::Virgo,
            6 => ZodiacSign::Libra,
            7 => ZodiacSign::Scorpio,
            8 => ZodiacSign::Sagittarius,
            9 => ZodiacSign::Capricorn,
            10 => ZodiacSign::Aquarius,
            _ => ZodiacSign::Pisces,
        };
        let sign_deg = norm - (sign_index as f64 * 30.0);
        (sign, sign_deg)
    }

    pub fn name_de(&self) -> &'static str {
        match self {
            ZodiacSign::Aries => "Widder",
            ZodiacSign::Taurus => "Stier",
            ZodiacSign::Gemini => "Zwillinge",
            ZodiacSign::Cancer => "Krebs",
            ZodiacSign::Leo => "Löwe",
            ZodiacSign::Virgo => "Jungfrau",
            ZodiacSign::Libra => "Waage",
            ZodiacSign::Scorpio => "Skorpion",
            ZodiacSign::Sagittarius => "Schütze",
            ZodiacSign::Capricorn => "Steinbock",
            ZodiacSign::Aquarius => "Wassermann",
            ZodiacSign::Pisces => "Fische",
        }
    }

    pub fn glyph(&self) -> &'static str {
        match self {
            ZodiacSign::Aries => "♈",
            ZodiacSign::Taurus => "♉",
            ZodiacSign::Gemini => "♊",
            ZodiacSign::Cancer => "♋",
            ZodiacSign::Leo => "♌",
            ZodiacSign::Virgo => "♍",
            ZodiacSign::Libra => "♎",
            ZodiacSign::Scorpio => "♏",
            ZodiacSign::Sagittarius => "♐",
            ZodiacSign::Capricorn => "♑",
            ZodiacSign::Aquarius => "♒",
            ZodiacSign::Pisces => "♓",
        }
    }

    pub fn element(&self) -> Element {
        match self {
            ZodiacSign::Aries | ZodiacSign::Leo | ZodiacSign::Sagittarius => Element::Fire,
            ZodiacSign::Taurus | ZodiacSign::Virgo | ZodiacSign::Capricorn => Element::Earth,
            ZodiacSign::Gemini | ZodiacSign::Libra | ZodiacSign::Aquarius => Element::Air,
            ZodiacSign::Cancer | ZodiacSign::Scorpio | ZodiacSign::Pisces => Element::Water,
        }
    }

    pub fn quality(&self) -> Quality {
        match self {
            ZodiacSign::Aries | ZodiacSign::Cancer | ZodiacSign::Libra | ZodiacSign::Capricorn => {
                Quality::Cardinal
            }
            ZodiacSign::Taurus | ZodiacSign::Leo | ZodiacSign::Scorpio | ZodiacSign::Aquarius => {
                Quality::Fixed
            }
            ZodiacSign::Gemini | ZodiacSign::Virgo | ZodiacSign::Sagittarius | ZodiacSign::Pisces => {
                Quality::Mutable
            }
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HouseSystemChoice {
    Placidus,
    Koch,
    Regiomontanus,
    Campanus,
    Equal,
    WholeSign,
    Topocentric,
    Porphyry,
}

impl HouseSystemChoice {
    pub fn to_sweph(&self) -> sweph::HouseSystem {
        match self {
            HouseSystemChoice::Placidus => sweph::HouseSystem::Placidus,
            HouseSystemChoice::Koch => sweph::HouseSystem::Koch,
            HouseSystemChoice::Regiomontanus => sweph::HouseSystem::Regiomontanus,
            HouseSystemChoice::Campanus => sweph::HouseSystem::Campanus,
            HouseSystemChoice::Equal => sweph::HouseSystem::Equal,
            HouseSystemChoice::WholeSign => sweph::HouseSystem::WholeSign,
            HouseSystemChoice::Topocentric => sweph::HouseSystem::Topocentric,
            HouseSystemChoice::Porphyry => sweph::HouseSystem::Porphyry,
        }
    }

    pub fn name_de(&self) -> &'static str {
        match self {
            HouseSystemChoice::Placidus => "Placidus",
            HouseSystemChoice::Koch => "Koch",
            HouseSystemChoice::Regiomontanus => "Regiomontanus",
            HouseSystemChoice::Campanus => "Campanus",
            HouseSystemChoice::Equal => "Äqual (Equal)",
            HouseSystemChoice::WholeSign => "Ganzzeichen (Whole Sign)",
            HouseSystemChoice::Topocentric => "Topozentrisch",
            HouseSystemChoice::Porphyry => "Porphyrius",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AspectType {
    Conjunction,
    SemiSextile,
    SemiSquare,
    Sextile,
    Quintile,
    Square,
    Trine,
    Sesquiquadrate,
    Quincunx,
    Opposition,
}

impl AspectType {
    pub fn target_angle(&self) -> f64 {
        match self {
            AspectType::Conjunction => 0.0,
            AspectType::SemiSextile => 30.0,
            AspectType::SemiSquare => 45.0,
            AspectType::Sextile => 60.0,
            AspectType::Quintile => 72.0,
            AspectType::Square => 90.0,
            AspectType::Trine => 120.0,
            AspectType::Sesquiquadrate => 135.0,
            AspectType::Quincunx => 150.0,
            AspectType::Opposition => 180.0,
        }
    }

    pub fn default_orb(&self) -> f64 {
        match self {
            AspectType::Conjunction => 8.0,
            AspectType::Opposition => 8.0,
            AspectType::Trine => 7.0,
            AspectType::Square => 7.0,
            AspectType::Sextile => 5.0,
            AspectType::Quincunx => 3.0,
            AspectType::SemiSquare | AspectType::Sesquiquadrate => 2.5,
            AspectType::Quintile | AspectType::SemiSextile => 2.0,
        }
    }

    pub fn glyph(&self) -> &'static str {
        match self {
            AspectType::Conjunction => "☌",
            AspectType::SemiSextile => "⚺",
            AspectType::SemiSquare => "∠",
            AspectType::Sextile => "⚹",
            AspectType::Quintile => "Q",
            AspectType::Square => "□",
            AspectType::Trine => "△",
            AspectType::Sesquiquadrate => "⚼",
            AspectType::Quincunx => "⚻",
            AspectType::Opposition => "☍",
        }
    }

    pub fn name_de(&self) -> &'static str {
        match self {
            AspectType::Conjunction => "Konjunktion",
            AspectType::SemiSextile => "Halbsextil",
            AspectType::SemiSquare => "Halbquadrat",
            AspectType::Sextile => "Sextil",
            AspectType::Quintile => "Quintil",
            AspectType::Square => "Quadrat",
            AspectType::Trine => "Trigon",
            AspectType::Sesquiquadrate => "Anderthalbquadrat",
            AspectType::Quincunx => "Quinkunx",
            AspectType::Opposition => "Opposition",
        }
    }

    pub fn color_hex(&self) -> &'static str {
        match self {
            AspectType::Conjunction => "#eab308",     // Gold
            AspectType::Sextile | AspectType::Trine => "#38bdf8", // Harmonious sky blue / cyan
            AspectType::Square | AspectType::Opposition => "#f43f5e", // Dynamic crimson/rose
            AspectType::Quincunx => "#a855f7",        // Purple mystery
            _ => "#94a3b8",                           // Subtle slate
        }
    }

    pub fn nature(&self) -> &'static str {
        match self {
            AspectType::Conjunction => "Synthese",
            AspectType::Trine | AspectType::Sextile => "Harmonisch",
            AspectType::Square | AspectType::Opposition => "Spannungsreich",
            AspectType::Quincunx => "Ambivalent",
            _ => "Nebenaspekt",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanetData {
    pub id: CelestialPoint,
    pub name: String,
    pub glyph: String,
    pub longitude: f64,
    pub latitude: f64,
    pub distance: f64,
    pub speed: f64,
    pub is_retrograde: bool,
    pub sign: ZodiacSign,
    pub sign_name: String,
    pub sign_glyph: String,
    pub sign_deg: f64,
    pub deg_int: u32,
    pub min_int: u32,
    pub sec_int: u32,
    pub formatted_deg: String,
    pub house: u8,
    pub dignity: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HouseCuspData {
    pub house_number: u8,
    pub longitude: f64,
    pub sign: ZodiacSign,
    pub sign_name: String,
    pub sign_glyph: String,
    pub deg_int: u32,
    pub min_int: u32,
    pub formatted_deg: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnglesData {
    pub ascendant: f64,
    pub ascendant_sign: ZodiacSign,
    pub ascendant_formatted: String,
    pub midheaven: f64,
    pub midheaven_sign: ZodiacSign,
    pub midheaven_formatted: String,
    pub descendant: f64,
    pub descendant_formatted: String,
    pub imum_coeli: f64,
    pub imum_coeli_formatted: String,
    pub part_of_fortune: f64,
    pub part_of_fortune_formatted: String,
    pub vertex: f64,
    pub vertex_formatted: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AspectData {
    pub point_a: CelestialPoint,
    pub point_a_name: String,
    pub point_a_glyph: String,
    pub point_b: CelestialPoint,
    pub point_b_name: String,
    pub point_b_glyph: String,
    pub aspect_type: AspectType,
    pub aspect_name: String,
    pub aspect_glyph: String,
    pub actual_angle: f64,
    pub target_angle: f64,
    pub orb: f64,
    pub formatted_orb: String,
    pub is_applying: bool,
    pub color_hex: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ElementQualitySummary {
    pub fire: u32,
    pub earth: u32,
    pub air: u32,
    pub water: u32,
    pub cardinal: u32,
    pub fixed: u32,
    pub mutable: u32,
    pub dominant_element: String,
    pub dominant_quality: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterpretationSection {
    pub title: String,
    pub subtitle: String,
    pub text: String,
    pub keywords: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartResponse {
    pub name: String,
    pub date_time: String,
    pub location_name: String,
    pub latitude: f64,
    pub longitude: f64,
    pub julian_day: f64,
    pub house_system: String,
    pub planets: Vec<PlanetData>,
    pub houses: Vec<HouseCuspData>,
    pub angles: AnglesData,
    pub aspects: Vec<AspectData>,
    pub element_quality: ElementQualitySummary,
    pub interpretations: Vec<InterpretationSection>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartRequest {
    pub name: String,
    pub year: i32,
    pub month: i32,
    pub day: i32,
    pub hour: u32,
    pub minute: u32,
    pub second: Option<u32>,
    pub timezone_offset: f64, // e.g. +1.0 for CET, +2.0 for CEST
    pub latitude: f64,
    pub longitude: f64,
    pub location_name: Option<String>,
    pub house_system: Option<HouseSystemChoice>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitRequest {
    pub natal: ChartRequest,
    pub transit_year: i32,
    pub transit_month: i32,
    pub transit_day: i32,
    pub transit_hour: u32,
    pub transit_minute: u32,
    pub transit_timezone_offset: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitToNatalAspect {
    pub transit_point: CelestialPoint,
    pub transit_name: String,
    pub transit_glyph: String,
    pub natal_point: CelestialPoint,
    pub natal_name: String,
    pub natal_glyph: String,
    pub aspect_type: AspectType,
    pub aspect_name: String,
    pub aspect_glyph: String,
    pub orb: f64,
    pub formatted_orb: String,
    pub color_hex: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitResponse {
    pub natal_chart: ChartResponse,
    pub transit_chart: ChartResponse,
    pub transit_aspects: Vec<TransitToNatalAspect>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynastryRequest {
    pub person_a: ChartRequest,
    pub person_b: ChartRequest,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SynastryResponse {
    pub chart_a: ChartResponse,
    pub chart_b: ChartResponse,
    pub cross_aspects: Vec<TransitToNatalAspect>,
    pub compatibility_notes: Vec<InterpretationSection>,
}
