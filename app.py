from flask import Flask, render_template, request

from weather_service import WeatherError, get_weather, get_weather_by_coordinates


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        city = request.args.get("city", "").strip()
        latitude = request.args.get("latitude", type=float)
        longitude = request.args.get("longitude", type=float)
        unit = request.args.get("unit", "celsius").lower()
        weather = None
        error = None

        if latitude is not None and longitude is not None:
            if unit not in {"celsius", "fahrenheit"}:
                error = "Please choose a valid temperature unit."
            else:
                try:
                    weather = get_weather_by_coordinates(latitude, longitude, unit)
                    city = weather.city
                except WeatherError as exc:
                    error = str(exc)
        elif city:
            if unit not in {"celsius", "fahrenheit"}:
                error = "Please choose a valid temperature unit."
            else:
                try:
                    weather = get_weather(city, unit)
                except WeatherError as exc:
                    error = str(exc)

        return render_template(
            "index.html",
            city=city,
            unit=unit if unit in {"celsius", "fahrenheit"} else "celsius",
            weather=weather,
            error=error,
            favorites=request.args.get("favorites", ""),
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
