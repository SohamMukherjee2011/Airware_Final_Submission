import requests
from config import get_settings
from exceptions import FetchError
from typing import Tuple, Dict, Any

settings = get_settings()
def _open_meteo_current_url(lat: float, lon: float) -> str:
    # Open-Meteo current weather + hourly/daily parameters
    # We'll request current hourly variables for the nearest hour (works without API key).
    base = "https://api.open-meteo.com/v1/forecast"
    # request hourly pm2_5/pm10 if available via the 'air_quality' parameter and current_weather
    params = (
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true"
        "&hourly=relativehumidity_2m,temperature_2m"
        "&timezone=auto"
        # Open-Meteo offers an air quality API (separate), but availability varies by config.
        # If you want PM variables from Open-Meteo's "air-quality" endpoint, you can call:
        # "&hourly=pm10,pm2_5" if supported for your region or use remote provider.
    )
    return base + params

def realtime_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Returns a dict:
    {
        "temp": float (C),
        "humidity": float (%),
        "pm25": float or None,
        "pm10": float or None,
        "descriptor": [strings],
        "raw": {...}  # optional raw response for debugging
    }
    """
    url = _open_meteo_current_url(lat, lon)
    try:
        resp = requests.get(url, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"Failed to fetch weather from Open-Meteo: {e}")

    # Extract current_weather and hourly/relative humidity if present
    temp = None
    humidity = None
    pm25 = None
    pm10 = None
    descriptor = []

    # current_weather usually contains temp and wind but not humidity
    cw = j.get("current_weather")
    if cw:
        temp = cw.get("temperature")  # open-meteo uses 'temperature' in current_weather
    # relative humidity may be present in hourly with timestamps; fallback to None
    hourly = j.get("hourly", {})
    # try to find the last available humidity for current hour
    try:
        rh_vals = hourly.get("relativehumidity_2m")
        time_vals = hourly.get("time")
        if rh_vals and time_vals:
            # pick the last value
            humidity = float(rh_vals[-1])
    except Exception:
        humidity = None

    # Attempt to extract pm if present in hourly
    try:
        pm25_vals = hourly.get("pm2_5") or hourly.get("pm2_5_ugm3") or hourly.get("pm25")
        pm10_vals = hourly.get("pm10")
        if pm25_vals:
            pm25 = float(pm25_vals[-1])
        if pm10_vals:
            pm10 = float(pm10_vals[-1])
    except Exception:
        pm25 = None
        pm10 = None

    # Basic descriptor creation
    if temp is not None:
        descriptor.append(f"{temp}°C")
    if humidity is not None:
        descriptor.append(f"RH {humidity}%")
    if pm25 is not None:
        descriptor.append(f"PM2.5 {pm25}")
    if pm10 is not None:
        descriptor.append(f"PM10 {pm10}")

    return {
        "temp": temp,
        "humidity": humidity,
        "pm25": pm25,
        "pm10": pm10,
        "descriptor": descriptor,
        "raw": j
    }

# Helper if user passes a city name: simple geocoding via Nominatim (optional)
def geocode_city_to_latlon(city: str) -> Tuple[float, float]:
    """
    Simple free geocode using Nominatim. Rate-limited; use with care.
    Returns (lat, lon)
    """
    try:
        url = ("https://nominatim.openstreetmap.org/search"
               f"?q={requests.utils.requote_uri(city)}&format=json&limit=1")
        resp = requests.get(url, headers={"User-Agent": "fetch-agent/0.1"}, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        arr = resp.json()
        if not arr:
            raise FetchError(f"Geocoding returned no results for {city}")
        item = arr[0]
        return float(item["lat"]), float(item["lon"])
    except FetchError:
        raise
    except Exception as e:
        raise FetchError(f"Failed geocoding city {city}: {e}")