use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Serialize, Deserialize)]
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
    Ceres,
    Pallas,
    Juno,
    Vesta,
    SouthNode,
    /// Achsen als Aspektpartner (nie in `settings.points()`)
    Ascendant,
    Midheaven,
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

    /// Die vier großen Asteroiden.
    pub fn asteroids() -> &'static [CelestialPoint] {
        &[
            CelestialPoint::Ceres,
            CelestialPoint::Pallas,
            CelestialPoint::Juno,
            CelestialPoint::Vesta,
        ]
    }

    /// Die zehn klassischen Planeten (Sonne bis Pluto).
    pub fn classical() -> &'static [CelestialPoint] {
        &Self::all()[..10]
    }

    /// Punkte, die nicht als „Planeten“ für Element-/Qualitätszählung gelten.
    pub fn is_sensitive_point(&self) -> bool {
        matches!(
            self,
            CelestialPoint::TrueNode
                | CelestialPoint::SouthNode
                | CelestialPoint::Chiron
                | CelestialPoint::Lilith
                | CelestialPoint::Ceres
                | CelestialPoint::Pallas
                | CelestialPoint::Juno
                | CelestialPoint::Vesta
        )
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
            CelestialPoint::Ceres => "Ceres",
            CelestialPoint::Pallas => "Pallas",
            CelestialPoint::Juno => "Juno",
            CelestialPoint::Vesta => "Vesta",
            CelestialPoint::SouthNode => "Südknoten",
            CelestialPoint::Ascendant => "Aszendent",
            CelestialPoint::Midheaven => "Medium Coeli",
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
            CelestialPoint::Ceres => "⚳",
            CelestialPoint::Pallas => "⚴",
            CelestialPoint::Juno => "⚵",
            CelestialPoint::Vesta => "⚶",
            CelestialPoint::SouthNode => "☋",
            CelestialPoint::Ascendant => "AC",
            CelestialPoint::Midheaven => "MC",
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
            CelestialPoint::Ceres => sweph::Body::Ceres,
            CelestialPoint::Pallas => sweph::Body::Pallas,
            CelestialPoint::Juno => sweph::Body::Juno,
            CelestialPoint::Vesta => sweph::Body::Vesta,
            CelestialPoint::SouthNode | CelestialPoint::Ascendant | CelestialPoint::Midheaven => sweph::Body::TrueNode,
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
            ZodiacSign::Aries => "♈\u{FE0E}",
            ZodiacSign::Taurus => "♉\u{FE0E}",
            ZodiacSign::Gemini => "♊\u{FE0E}",
            ZodiacSign::Cancer => "♋\u{FE0E}",
            ZodiacSign::Leo => "♌\u{FE0E}",
            ZodiacSign::Virgo => "♍\u{FE0E}",
            ZodiacSign::Libra => "♎\u{FE0E}",
            ZodiacSign::Scorpio => "♏\u{FE0E}",
            ZodiacSign::Sagittarius => "♐\u{FE0E}",
            ZodiacSign::Capricorn => "♑\u{FE0E}",
            ZodiacSign::Aquarius => "♒\u{FE0E}",
            ZodiacSign::Pisces => "♓\u{FE0E}",
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
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

    /// Buchstabencode der Swiss Ephemeris.
    pub fn code(&self) -> u8 {
        match self {
            HouseSystemChoice::Placidus => b'P',
            HouseSystemChoice::Koch => b'K',
            HouseSystemChoice::Regiomontanus => b'R',
            HouseSystemChoice::Campanus => b'C',
            HouseSystemChoice::Equal => b'A',
            HouseSystemChoice::WholeSign => b'W',
            HouseSystemChoice::Topocentric => b'T',
            HouseSystemChoice::Porphyry => b'O',
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

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
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
    /// Deklination (für Parallelaspekte)
    #[serde(default)]
    pub declination: f64,
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
    #[serde(default)]
    pub timezone_info: Option<crate::astrology::tz::TzInfo>,
    #[serde(default)]
    pub analysis: Option<crate::astrology::analysis::AnalysisData>,
    #[serde(default)]
    pub zodiac: Zodiac,
    #[serde(default)]
    pub ayanamsa_name: Option<String>,
    #[serde(default)]
    pub ayanamsa_value: Option<f64>,
    /// Tageshoroskop (Sonne über dem Horizont)
    #[serde(default)]
    pub is_diurnal: bool,
    /// Ob Swiss-Ephemeris-Datendateien verwendet wurden (sonst Moshier/Tabellen)
    #[serde(default)]
    pub ephemeris_files: bool,
}

/// Mondknoten: wahr oder mittel.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum NodeType {
    #[default]
    True,
    Mean,
}

/// Lilith: mittleres oder oskulierendes Apogäum.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum LilithType {
    #[default]
    Mean,
    Osculating,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Default)]
pub enum Zodiac {
    #[default]
    Tropical,
    Sidereal,
}

fn default_true() -> bool {
    true
}
fn default_lahiri() -> i32 {
    1
}
fn default_luminary_bonus() -> f64 {
    1.5
}
fn default_minor_reduction() -> f64 {
    1.5
}
fn default_star_orb() -> f64 {
    1.0
}
fn default_language() -> String {
    "de".into()
}
fn default_aspects() -> Vec<AspectType> {
    vec![
        AspectType::Conjunction,
        AspectType::Opposition,
        AspectType::Trine,
        AspectType::Square,
        AspectType::Sextile,
        AspectType::Quincunx,
        AspectType::SemiSquare,
        AspectType::Sesquiquadrate,
        AspectType::SemiSextile,
        AspectType::Quintile,
    ]
}

/// Berechnungseinstellungen. Alle Felder sind optional; fehlende Felder haben das
/// bisherige Standardverhalten.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(default)]
pub struct ChartSettings {
    pub node: NodeType,
    pub lilith: LilithType,
    /// Ceres, Pallas, Juno, Vesta
    pub asteroids: bool,
    /// Südknoten als eigener Punkt
    pub south_node: bool,
    pub zodiac: Zodiac,
    /// Swiss-Ephemeris-Ayanamsa-ID (nur bei `Sidereal`), Standard Lahiri
    #[serde(default = "default_lahiri")]
    pub ayanamsa: i32,
    /// Topozentrische Positionen (wirkt vor allem beim Mond)
    pub topocentric: bool,
    /// Orbis je Aspekt (überschreibt den Standard)
    pub orbs: HashMap<AspectType, f64>,
    /// Zuschlag für Sonne/Mond
    #[serde(default = "default_luminary_bonus")]
    pub luminary_bonus: f64,
    /// Abschlag für Knoten/Chiron/Lilith/Asteroiden
    #[serde(default = "default_minor_reduction")]
    pub minor_point_reduction: f64,
    /// Welche Aspekte gesucht werden
    #[serde(default = "default_aspects")]
    pub aspects: Vec<AspectType>,
    /// Fixstern-Konjunktionen berechnen
    #[serde(default = "default_true")]
    pub fixed_stars: bool,
    #[serde(default = "default_star_orb")]
    pub fixed_star_orb: f64,
    /// Zusatzanalysen (Würden, Figuren, Halbsummen, Lose)
    #[serde(default = "default_true")]
    pub analysis: bool,
    /// "de" oder "en"
    #[serde(default = "default_language")]
    pub language: String,
}

impl Default for ChartSettings {
    fn default() -> Self {
        ChartSettings {
            node: NodeType::True,
            lilith: LilithType::Mean,
            asteroids: false,
            south_node: false,
            zodiac: Zodiac::Tropical,
            ayanamsa: 1,
            topocentric: false,
            orbs: HashMap::new(),
            luminary_bonus: 1.5,
            minor_point_reduction: 1.5,
            aspects: default_aspects(),
            fixed_stars: true,
            fixed_star_orb: 1.0,
            analysis: true,
            language: "de".into(),
        }
    }
}

impl ChartSettings {
    pub fn orb_for(&self, aspect: AspectType) -> f64 {
        self.orbs.get(&aspect).copied().unwrap_or_else(|| aspect.default_orb())
    }

    /// Welche Punkte berechnet werden.
    pub fn points(&self) -> Vec<CelestialPoint> {
        let mut v: Vec<CelestialPoint> = CelestialPoint::all().to_vec();
        if self.asteroids {
            v.extend_from_slice(CelestialPoint::asteroids());
        }
        if self.south_node {
            v.push(CelestialPoint::SouthNode);
        }
        v
    }
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
    /// Offset zu UTC in Stunden. Wird ignoriert, wenn `timezone` gesetzt ist.
    #[serde(default)]
    pub timezone_offset: f64,
    pub latitude: f64,
    pub longitude: f64,
    pub location_name: Option<String>,
    pub house_system: Option<HouseSystemChoice>,
    /// IANA-Zone (z. B. "Europe/Berlin"): Offset und Sommerzeit werden historisch aufgelöst.
    #[serde(default)]
    pub timezone: Option<String>,
    #[serde(default)]
    pub settings: Option<ChartSettings>,
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
    /// Aspekt wird exakter (Annäherung) statt weiter zu laufen
    #[serde(default)]
    pub is_applying: bool,
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
    #[serde(default)]
    pub composite_chart: Option<ChartResponse>,
    #[serde(default)]
    pub davison_chart: Option<ChartResponse>,
    #[serde(default)]
    pub overlay_a_in_b: Vec<crate::astrology::synastry::OverlayEntry>,
    #[serde(default)]
    pub overlay_b_in_a: Vec<crate::astrology::synastry::OverlayEntry>,
    #[serde(default)]
    pub grid: crate::astrology::synastry::AspectGrid,
}
