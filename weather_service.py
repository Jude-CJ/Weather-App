from dataclasses import dataclass
from typing import Any

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 8


class WeatherError(Exception):
    """An expected error while looking up weather data."""


@dataclass(frozen=True)
class Weather:
    city: str
    region: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    wind_speed: float
    wind_direction: int
    high: float
    low: float
    condition: str
    icon: str
    unit_symbol: str


WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy drizzle", "🌧️"),
    56: ("Freezing drizzle", "🌧️"),
    57: ("Heavy freezing drizzle", "🌧️"),
    61: ("Light rain", "🌦️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Light showers", "🌦️"),
    81: ("Showers", "🌧️"),
    82: ("Heavy showers", "🌧️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


def weather_code_details(code: int) -> tuple[str, str]:
    return WEATHER_CODES.get(code, ("Unknown conditions", "•"))


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherError("Weather data is temporarily unavailable. Please try again.") from exc

    if not isinstance(payload, dict):
        raise WeatherError("The weather service returned an unexpected response.")
    return payload


def _find_location(city: str) -> dict[str, Any]:
    payload = _get_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = payload.get("results")
    if not results:
        raise WeatherError(f"We could not find a location named {city}.")
    return results[0]


def _number(values: Any, index: int = 0) -> float:
    value = values[index] if isinstance(values, list) else values
    if not isinstance(value, (int, float)):
        raise WeatherError("The weather service returned incomplete data.")
    return float(value)


def get_weather(city: str, unit: str = "celsius") -> Weather:
    location = _find_location(city)
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise WeatherError("The location response was incomplete.")

    temperature_unit = unit if unit in {"celsius", "fahrenheit"} else "celsius"
    payload = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": temperature_unit,
            "wind_speed_unit": "kmh",
            "timezone": "auto",
            "forecast_days": 1,
        },
    )

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    try:
        condition, icon = weather_code_details(int(current["weather_code"]))
        return Weather(
            city=str(location.get("name", city)),
            region=str(location.get("admin1") or ""),
            country=str(location.get("country") or ""),
            temperature=_number(current["temperature_2m"]),
            feels_like=_number(current["apparent_temperature"]),
            humidity=int(_number(current["relative_humidity_2m"])),
            wind_speed=_number(current["wind_speed_10m"]),
            wind_direction=int(_number(current["wind_direction_10m"])),
            high=_number(daily["temperature_2m_max"]),
            low=_number(daily["temperature_2m_min"]),
            condition=condition,
            icon=icon,
            unit_symbol="°F" if temperature_unit == "fahrenheit" else "°C",
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("The weather service returned incomplete data.") from exc
