"""
BuildSense Tool: Weather & Site Condition Advisory
Milestone 2: Tool Integration & Action Execution

Fetches current weather data using OpenWeatherMap API and generates
construction-site-specific risk advisories.

Live mode:   Calls api.openweathermap.org with WEATHER_API_KEY from .env
Simulation:  Returns a realistic monsoon scenario for Pune if key is absent or request fails
"""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenWeatherMap free-tier endpoint
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Risk thresholds for construction advisories
RAIN_RISK_THRESHOLD_MM = 5.0     # mm/h — above this flags concrete/plastering risk
WIND_RISK_THRESHOLD_KMH = 40.0   # km/h — flags scaffolding safety risk
HEAT_RISK_THRESHOLD_C = 38.0     # °C   — flags heat stress / water curing risk

SIMULATION_DATA = {
    "city": "Pune",
    "country": "IN",
    "temp_c": 28.5,
    "feels_like_c": 31.2,
    "humidity_pct": 82,
    "condition": "Light Rain",
    "condition_icon": "🌧️",
    "rainfall_1h_mm": 3.8,
    "wind_speed_kmh": 18.0,
    "visibility_km": 6.0,
    "source": "Simulation (OpenWeatherMap key not configured)"
}


def _generate_advisory(weather: dict) -> dict:
    """
    Generates construction-site advisories based on weather conditions.
    Returns a risk_level ('LOW', 'MEDIUM', 'HIGH') and advisory list.
    """
    advisories = []
    risk_level = "LOW"

    rain_mm = weather.get("rainfall_1h_mm", 0.0)
    wind_kmh = weather.get("wind_speed_kmh", 0.0)
    temp_c = weather.get("temp_c", 25.0)
    humidity = weather.get("humidity_pct", 50)

    # Rain checks
    if rain_mm > RAIN_RISK_THRESHOLD_MM:
        risk_level = "HIGH"
        advisories.append(
            f"⛔ STOP concrete pouring — rainfall {rain_mm:.1f}mm/h exceeds safe threshold ({RAIN_RISK_THRESHOLD_MM}mm/h). "
            "Water contamination compromises concrete mix ratio (NBC Part 6, Clause 7.2)."
        )
        advisories.append(
            "⛔ Suspend plastering and putty application — high moisture prevents proper curing and bonding."
        )
    elif rain_mm > 1.0:
        risk_level = max(risk_level, "MEDIUM") if risk_level != "HIGH" else "HIGH"
        advisories.append(
            f"⚠️ Light rainfall ({rain_mm:.1f}mm/h) detected. Protect freshly poured slabs and mortar joints "
            "with curing sheets. Delay plaster finishing coats."
        )

    # Wind checks
    if wind_kmh > WIND_RISK_THRESHOLD_KMH:
        risk_level = "HIGH"
        advisories.append(
            f"⛔ HIGH WIND ALERT ({wind_kmh:.0f} km/h) — secure all scaffolding and formwork. "
            "Suspend crane/lift operations per OSHA scaffold safety standards."
        )
    elif wind_kmh > 25:
        if risk_level == "LOW":
            risk_level = "MEDIUM"
        advisories.append(
            f"⚠️ Moderate wind ({wind_kmh:.0f} km/h) — ensure scaffolding bracing is properly tightened. "
            "Avoid transporting lightweight sheet materials (gypsum, glass)."
        )

    # Heat stress check
    if temp_c > HEAT_RISK_THRESHOLD_C:
        if risk_level == "LOW":
            risk_level = "MEDIUM"
        advisories.append(
            f"⚠️ High temperature ({temp_c:.1f}°C) — implement mandatory rest breaks every 2 hrs for workers. "
            "Increase concrete curing water frequency (every 4 hrs instead of 8)."
        )

    # Humidity check for painting
    if humidity > 85:
        if risk_level == "LOW":
            risk_level = "MEDIUM"
        advisories.append(
            f"⚠️ High humidity ({humidity}%) — delay exterior painting and waterproofing application. "
            "Paint requires humidity < 85% for proper adhesion and drying."
        )

    if not advisories:
        advisories.append(
            "✅ Weather conditions are favourable for all construction activities. "
            "Proceed as scheduled."
        )

    return {
        "risk_level": risk_level,
        "advisories": advisories,
        "safe_activities": _get_safe_activities(risk_level),
        "restricted_activities": _get_restricted_activities(rain_mm, wind_kmh, temp_c, humidity)
    }


def _get_safe_activities(risk_level: str) -> list:
    if risk_level == "LOW":
        return [
            "Concrete pouring & curing",
            "Masonry & brickwork",
            "Plastering & putty",
            "Tiling & flooring",
            "Painting (interior & exterior)",
            "Scaffolding & elevated work"
        ]
    elif risk_level == "MEDIUM":
        return [
            "Structural masonry (covered areas)",
            "Interior tiling & flooring",
            "Electrical conduit work",
            "Carpentry & woodwork (indoor)"
        ]
    else:  # HIGH
        return [
            "Interior electrical work (non-elevated)",
            "Material procurement & planning",
            "Site supervision & documentation",
            "Indoor fixture installations"
        ]


def _get_restricted_activities(rain_mm, wind_kmh, temp_c, humidity):
    restricted = []
    if rain_mm > RAIN_RISK_THRESHOLD_MM:
        restricted.extend([
            "Concrete pouring / RCC work",
            "Plastering & wall putty",
            "Exterior waterproofing"
        ])
    if wind_kmh > WIND_RISK_THRESHOLD_KMH:
        restricted.extend([
            "Scaffolding erection / dismantling",
            "Crane & material hoisting",
            "Sheet material handling (gypsum, glass)"
        ])
    if temp_c > HEAT_RISK_THRESHOLD_C:
        restricted.append("Outdoor heavy labour (12:00 – 15:00)")
    if humidity > 85:
        restricted.extend(["Exterior painting", "Waterproof membrane application"])
    return list(set(restricted))


def get_weather_advisory(city: str = "Pune", country_code: str = "IN") -> dict:
    """
    Fetch current weather and return a construction site advisory.
    
    Args:
        city:         City name (e.g. 'Pune', 'Mumbai', 'Delhi')
        country_code: ISO 3166-1 alpha-2 code (default 'IN')
    
    Returns:
        dict with weather data, risk_level, advisories, safe/restricted activities
    
    Falls back to simulation data if WEATHER_API_KEY is not set or request fails.
    """
    api_key = os.getenv("WEATHER_API_KEY", "").strip()
    
    if api_key:
        try:
            import requests
            params = {
                "q": f"{city},{country_code}",
                "appid": api_key,
                "units": "metric"   # Celsius
            }
            response = requests.get(OWM_BASE_URL, params=params, timeout=8)
            response.raise_for_status()
            data = response.json()
            
            # Parse OpenWeatherMap response
            weather_data = {
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", country_code),
                "temp_c": round(data.get("main", {}).get("temp", 25.0), 1),
                "feels_like_c": round(data.get("main", {}).get("feels_like", 25.0), 1),
                "humidity_pct": data.get("main", {}).get("humidity", 50),
                "condition": data.get("weather", [{}])[0].get("description", "Clear").title(),
                "condition_icon": _get_condition_icon(
                    data.get("weather", [{}])[0].get("main", "Clear")
                ),
                "rainfall_1h_mm": data.get("rain", {}).get("1h", 0.0),
                "wind_speed_kmh": round(data.get("wind", {}).get("speed", 0) * 3.6, 1),  # m/s → km/h
                "visibility_km": round(data.get("visibility", 10000) / 1000, 1),
                "source": f"OpenWeatherMap Live API — {city}, {country_code}"
            }
            advisory = _generate_advisory(weather_data)
            return {**weather_data, **advisory}
            
        except Exception as e:
            print(f"[WeatherTool] OpenWeatherMap API failed: {e}. Using simulation data.")
            source_note = f"Simulation (API error: {type(e).__name__})"
    else:
        print("[WeatherTool] WEATHER_API_KEY not set. Using simulation data.")
        source_note = "Simulation (WEATHER_API_KEY not configured — add to .env)"
    
    # Simulation fallback
    sim = dict(SIMULATION_DATA)
    sim["city"] = city
    sim["source"] = source_note
    advisory = _generate_advisory(sim)
    return {**sim, **advisory}


def _get_condition_icon(main_condition: str) -> str:
    """Maps OpenWeatherMap condition codes to emoji icons."""
    icons = {
        "Clear": "☀️",
        "Clouds": "⛅",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️",
        "Dust": "💨",
        "Smoke": "💨"
    }
    return icons.get(main_condition, "🌤️")
