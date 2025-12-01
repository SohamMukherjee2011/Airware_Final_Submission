import requests
from config import get_settings
from exceptions import FetchError

settings = get_settings()
def _build_aqicn_url_for_location(location: str) -> str:
    """
    AQICN accepts city names like 'delhi' or geo:lat;lon
    e.g. https://api.waqi.info/feed/geo:10.3;76.4/?token=TOKEN
    """
    token = settings.AQICN_TOKEN
    if not token:
        raise FetchError("AQICN_TOKEN not set in environment")

    if "," in location:
        lat, lon = [p.strip() for p in location.split(",")]
        return f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={token}"
    else:
        # city name or station id
        return f"https://api.waqi.info/feed/{location}/?token={token}"

def realtime_aqi(location: str) -> int:
    """
    Returns integer AQI for the location.
    location: "CityName" or "lat,lon" (e.g., "22.5726,88.3639")
    Raises FetchError on failure.
    """
    url = _build_aqicn_url_for_location(location)
    try:
        resp = requests.get(url, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"HTTP error fetching AQI: {e}")

    # WAQI JSON usually: {"status":"ok", "data": {...}}
    if not isinstance(j, dict):
        raise FetchError("Unexpected response format from AQICN")

    if j.get("status") != "ok":
        # Handle some known failure modes gracefully
        msg = j.get("data") or j.get("message") or "unknown"
        raise FetchError(f"AQICN status not ok: {msg}")

    data = j.get("data", {})
    # AQI number might be in data["aqi"]
    aqi = data.get("aqi")
    if aqi is None:
        # try to pick from iaqi fields (pm25 etc.) if present, but prefer aqi if available
        iaqi = data.get("iaqi") or {}
        pm25 = iaqi.get("pm25", {}).get("v")
        pm10 = iaqi.get("pm10", {}).get("v")
        # fallback heuristic: return pm25 as proxy if present
        if pm25 is not None:
            try:
                return int(pm25)
            except Exception:
                pass
        raise FetchError("AQI value missing in AQICN response")

    try:
        return int(aqi)
    except Exception as e:
        raise FetchError(f"Failed to parse AQI value: {e}")