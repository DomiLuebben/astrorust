use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CityEntry {
    pub name: String,
    pub country: String,
    pub latitude: f64,
    pub longitude: f64,
    pub default_tz: f64,
}

pub fn get_atlas() -> Vec<CityEntry> {
    vec![
        // Deutschland
        CityEntry { name: "Berlin".into(), country: "Deutschland".into(), latitude: 52.5200, longitude: 13.4050, default_tz: 1.0 },
        CityEntry { name: "München".into(), country: "Deutschland".into(), latitude: 48.1351, longitude: 11.5820, default_tz: 1.0 },
        CityEntry { name: "Hamburg".into(), country: "Deutschland".into(), latitude: 53.5511, longitude: 9.9937, default_tz: 1.0 },
        CityEntry { name: "Köln".into(), country: "Deutschland".into(), latitude: 50.9375, longitude: 6.9603, default_tz: 1.0 },
        CityEntry { name: "Frankfurt am Main".into(), country: "Deutschland".into(), latitude: 50.1109, longitude: 8.6821, default_tz: 1.0 },
        CityEntry { name: "Stuttgart".into(), country: "Deutschland".into(), latitude: 48.7758, longitude: 9.1829, default_tz: 1.0 },
        CityEntry { name: "Düsseldorf".into(), country: "Deutschland".into(), latitude: 51.2277, longitude: 6.7735, default_tz: 1.0 },
        CityEntry { name: "Leipzig".into(), country: "Deutschland".into(), latitude: 51.3397, longitude: 12.3731, default_tz: 1.0 },
        CityEntry { name: "Dresden".into(), country: "Deutschland".into(), latitude: 51.0504, longitude: 13.7373, default_tz: 1.0 },
        CityEntry { name: "Nürnberg".into(), country: "Deutschland".into(), latitude: 49.4521, longitude: 11.0767, default_tz: 1.0 },
        CityEntry { name: "Hannover".into(), country: "Deutschland".into(), latitude: 52.3759, longitude: 9.7320, default_tz: 1.0 },
        CityEntry { name: "Bremen".into(), country: "Deutschland".into(), latitude: 53.0793, longitude: 8.8017, default_tz: 1.0 },
        CityEntry { name: "Ulm".into(), country: "Deutschland".into(), latitude: 48.4011, longitude: 9.9876, default_tz: 1.0 },
        CityEntry { name: "Freiburg im Breisgau".into(), country: "Deutschland".into(), latitude: 47.9990, longitude: 7.8421, default_tz: 1.0 },

        // Österreich
        CityEntry { name: "Wien".into(), country: "Österreich".into(), latitude: 48.2082, longitude: 16.3738, default_tz: 1.0 },
        CityEntry { name: "Graz".into(), country: "Österreich".into(), latitude: 47.0707, longitude: 15.4395, default_tz: 1.0 },
        CityEntry { name: "Linz".into(), country: "Österreich".into(), latitude: 48.3069, longitude: 14.2858, default_tz: 1.0 },
        CityEntry { name: "Salzburg".into(), country: "Österreich".into(), latitude: 47.8095, longitude: 13.0550, default_tz: 1.0 },
        CityEntry { name: "Innsbruck".into(), country: "Österreich".into(), latitude: 47.2692, longitude: 11.4041, default_tz: 1.0 },
        CityEntry { name: "Klagenfurt".into(), country: "Österreich".into(), latitude: 46.6247, longitude: 14.3053, default_tz: 1.0 },

        // Schweiz
        CityEntry { name: "Zürich".into(), country: "Schweiz".into(), latitude: 47.3769, longitude: 8.5417, default_tz: 1.0 },
        CityEntry { name: "Bern".into(), country: "Schweiz".into(), latitude: 46.9480, longitude: 7.4474, default_tz: 1.0 },
        CityEntry { name: "Basel".into(), country: "Schweiz".into(), latitude: 47.5596, longitude: 7.5886, default_tz: 1.0 },
        CityEntry { name: "Genf".into(), country: "Schweiz".into(), latitude: 46.2044, longitude: 6.1432, default_tz: 1.0 },
        CityEntry { name: "Luzern".into(), country: "Schweiz".into(), latitude: 47.0502, longitude: 8.3093, default_tz: 1.0 },
        CityEntry { name: "Kesswil".into(), country: "Schweiz".into(), latitude: 47.5954, longitude: 9.3175, default_tz: 1.0 },

        // Europa & Welt
        CityEntry { name: "London".into(), country: "Großbritannien".into(), latitude: 51.5074, longitude: -0.1278, default_tz: 0.0 },
        CityEntry { name: "Paris".into(), country: "Frankreich".into(), latitude: 48.8566, longitude: 2.3522, default_tz: 1.0 },
        CityEntry { name: "Rom".into(), country: "Italien".into(), latitude: 41.9028, longitude: 12.4964, default_tz: 1.0 },
        CityEntry { name: "Vinci".into(), country: "Italien".into(), latitude: 43.7844, longitude: 10.9250, default_tz: 1.0 },
        CityEntry { name: "Madrid".into(), country: "Spanien".into(), latitude: 40.4168, longitude: -3.7038, default_tz: 1.0 },
        CityEntry { name: "Amsterdam".into(), country: "Niederlande".into(), latitude: 52.3676, longitude: 4.9041, default_tz: 1.0 },
        CityEntry { name: "Prag".into(), country: "Tschechien".into(), latitude: 50.0755, longitude: 14.4378, default_tz: 1.0 },
        CityEntry { name: "Warschau".into(), country: "Polen".into(), latitude: 52.2297, longitude: 21.0122, default_tz: 1.0 },
        CityEntry { name: "Athen".into(), country: "Griechenland".into(), latitude: 37.9838, longitude: 23.7275, default_tz: 2.0 },
        CityEntry { name: "Stockholm".into(), country: "Schweden".into(), latitude: 59.3293, longitude: 18.0686, default_tz: 1.0 },
        CityEntry { name: "New York".into(), country: "USA".into(), latitude: 40.7128, longitude: -74.0060, default_tz: -5.0 },
        CityEntry { name: "Los Angeles".into(), country: "USA".into(), latitude: 34.0522, longitude: -118.2437, default_tz: -8.0 },
        CityEntry { name: "San Francisco".into(), country: "USA".into(), latitude: 37.7749, longitude: -122.4194, default_tz: -8.0 },
        CityEntry { name: "Tokio".into(), country: "Japan".into(), latitude: 35.6762, longitude: 139.6503, default_tz: 9.0 },
        CityEntry { name: "Sydney".into(), country: "Australien".into(), latitude: -33.8688, longitude: 151.2093, default_tz: 10.0 },
        CityEntry { name: "Kairo".into(), country: "Ägypten".into(), latitude: 30.0444, longitude: 31.2357, default_tz: 2.0 },
    ]
}

pub fn search_cities(query: &str) -> Vec<CityEntry> {
    let q = query.trim().to_lowercase();
    if q.is_empty() {
        return get_atlas();
    }
    get_atlas()
        .into_iter()
        .filter(|c| c.name.to_lowercase().contains(&q) || c.country.to_lowercase().contains(&q))
        .collect()
}
