from unittest.mock import Mock, patch

from app import app
from weather_service import Weather, WeatherError, weather_code_details


def test_weather_code_mapping():
    assert weather_code_details(0) == ("Clear sky", "☀️")
    assert weather_code_details(63) == ("Rain", "🌧️")
    assert weather_code_details(999) == ("Unknown conditions", "•")


def test_home_page_has_search_form():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert b"Search a city" in response.data
    assert b"see its conditions" in response.data


def test_successful_weather_lookup():
    weather = Weather(
        city="London", region="England", country="United Kingdom",
        temperature=18, feels_like=17, humidity=72, wind_speed=12,
        wind_direction=240, high=20, low=11, condition="Rain", icon="🌧️",
        unit_symbol="°C",
    )
    with patch("app.get_weather", return_value=weather) as get_weather:
        response = app.test_client().get("/?city=London&unit=celsius")

    assert response.status_code == 200
    assert b"London" in response.data
    assert b"Rain" in response.data
    assert b"18" in response.data
    get_weather.assert_called_once_with("London", "celsius")


def test_weather_error_is_rendered():
    with patch("app.get_weather", side_effect=WeatherError("City not found.")):
        response = app.test_client().get("/?city=Atlantis")

    assert response.status_code == 200
    assert b"City not found." in response.data
    assert b"Could not load that forecast" in response.data


def test_invalid_unit_does_not_call_service():
    with patch("app.get_weather") as get_weather:
        response = app.test_client().get("/?city=London&unit=kelvin")

    assert response.status_code == 200
    assert b"valid temperature unit" in response.data
    get_weather.assert_not_called()
