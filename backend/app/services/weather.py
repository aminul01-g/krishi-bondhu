
import requests

def call_open_meteo(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly":"temperature_2m,relativehumidity_2m,precipitation", "timezone":"auto"}
    try:
        r = requests.get(url, params=params, timeout=10)
        return r.json()
    except Exception:
        return {}

def weather_node(state):
    gps = state.get("gps")
    if not gps or not gps.get("lat") or not gps.get("lon"):
        return {}
    w = call_open_meteo(gps.get("lat"), gps.get("lon"))
    return {"weather_forecast": w}
