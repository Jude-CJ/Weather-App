# Skyline Weather

A small Flask weather dashboard powered by the Open-Meteo geocoding and forecast APIs. It does not require an API key.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and search for a city. Use the unit selector to switch between Celsius and Fahrenheit.

## Test

```powershell
python -m pytest
```

The tests mock all Open-Meteo requests, so they do not require internet access.
