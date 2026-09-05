from dataclasses import dataclass, field
from typing import Any

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REVERSE_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
REQUEST_TIMEOUT = 8


class WeatherError(Exception):
    """An expected error while looking up weather data."""


@dataclass(frozen=True)
class HourlyForecast:
    time: str
    temperature: float
    weather_code: int
    condition: str
    icon: str


@dataclass(frozen=True)
class DailyForecast:
    date: str
    high: float
    low: float
    weather_code: int
    condition: str
    icon: str


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
    wind_unit: str = "km/h"
    theme: str = "clear"
    hourly: list[HourlyForecast] = field(default_factory=list)
    daily: list[DailyForecast] = field(default_factory=list)


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


def weather_theme(code: int) -> str:
    if code >= 95:
        return "storm"
    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "snow"
    if code in {2, 3, 45, 48}:
        return "cloudy"
    return "sunny"


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


def _reverse_geocode(latitude: float, longitude: float) -> tuple[str, str, str]:
    try:
        response = requests.get(
            REVERSE_GEOCODING_URL,
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 18,
                "addressdetails": 1,
            },
            headers={"User-Agent": "SkylineWeather/1.0"},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        address = payload.get("address", {})
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("locality")
            or address.get("city_district")
            or address.get("suburb")
            or address.get("county")
        )
        region = address.get("state") or address.get("county") or ""
        country = address.get("country") or ""
        if city:
            return str(city), str(region), str(country)
        display_name = payload.get("display_name")
        if isinstance(display_name, str) and display_name.strip():
            return display_name.split(",", 1)[0].strip(), str(region), str(country)
    except (requests.RequestException, ValueError, AttributeError, TypeError):
        pass
    return "Location unavailable", "", ""


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

    return _get_weather_for_coordinates(
        latitude,
        longitude,
        unit,
        city_name=str(location.get("name", city)),
        region=str(location.get("admin1") or ""),
        country=str(location.get("country") or ""),
    )


def get_weather_by_coordinates(latitude: float, longitude: float, unit: str = "celsius") -> Weather:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise WeatherError("The location coordinates were invalid.")
    city, region, country = _reverse_geocode(latitude, longitude)
    return _get_weather_for_coordinates(latitude, longitude, unit, city, region, country)


def _get_weather_for_coordinates(
    latitude: float,
    longitude: float,
    unit: str,
    city_name: str,
    region: str,
    country: str,
) -> Weather:

    temperature_unit = unit if unit in {"celsius", "fahrenheit"} else "celsius"
    payload = _get_json(
        FORECAST_URL,
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "temperature_unit": temperature_unit,
            "wind_speed_unit": "mph" if temperature_unit == "fahrenheit" else "kmh",
            "timezone": "auto",
            "forecast_days": 7,
        },
    )

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    hourly = payload.get("hourly", {})
    try:
        current_code = int(current["weather_code"])
        condition, icon = weather_code_details(current_code)
        hourly_times = hourly["time"][:24]
        hourly_temperatures = hourly["temperature_2m"][:24]
        hourly_codes = hourly["weather_code"][:24]
        hourly_forecast = [
            HourlyForecast(
                time=str(time),
                temperature=float(temperature),
                weather_code=int(code),
                condition=weather_code_details(int(code))[0],
                icon=weather_code_details(int(code))[1],
            )
            for time, temperature, code in zip(hourly_times, hourly_temperatures, hourly_codes)
        ]
        daily_forecast = [
            DailyForecast(
                date=str(date),
                high=float(high),
                low=float(low),
                weather_code=int(code),
                condition=weather_code_details(int(code))[0],
                icon=weather_code_details(int(code))[1],
            )
            for date, high, low, code in zip(
                daily["time"], daily["temperature_2m_max"], daily["temperature_2m_min"], daily["weather_code"]
            )
        ]
        return Weather(
            city=city_name,
            region=region,
            country=country,
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
            wind_unit="mph" if temperature_unit == "fahrenheit" else "km/h",
            theme=weather_theme(current_code),
            hourly=hourly_forecast,
            daily=daily_forecast,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("The weather service returned incomplete data.") from exc
