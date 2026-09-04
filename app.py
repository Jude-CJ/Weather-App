from flask import Flask, render_template, request

from weather_service import WeatherError, get_weather


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        city = request.args.get("city", "").strip()
        unit = request.args.get("unit", "celsius").lower()
        weather = None
        error = None

        if city:
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
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
