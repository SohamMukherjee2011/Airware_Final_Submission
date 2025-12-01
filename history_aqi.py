import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from .exceptions import FetchError
from .config import get_settings
settings = get_settings()
OPENAQ_API_KEY = settings.OPENAQ_TOKEN
BASE_URL = "https://api.openaq.org/v3"
PM25_PARAMETER_ID = 2 

def _headers() -> Dict[str, str]:
    if not OPENAQ_API_KEY:
        raise FetchError("OPENAQ_API_KEY not set in environment")
    return {"X-API-Key": OPENAQ_API_KEY}

def _compute_datetime_range_iso(months: int) -> tuple[str, str]:
    """
    Returns (datetime_from, datetime_to) as ISO8601 strings (UTC) for the last `months` calendar months.

    Example: if today is 2025-11-25 and months=12,
    datetime_from ~ 2024-12-01T00:00:00Z, datetime_to = now.
    """
    if months < 1:
        months = 1

    now = datetime.utcnow()
    year = now.year
    month = now.month
    total_months = year * 12 + (month - 1) - (months - 1)
    start_year = total_months // 12
    start_month = total_months % 12 + 1
    dt_from = datetime(start_year, start_month, 1)
    dt_to = now
    return dt_from.isoformat(timespec="seconds") + "Z", dt_to.isoformat(timespec="seconds") + "Z"


def _is_lat_lon(location: str) -> bool:
    return "," in location and len(location.split(",")) == 2


def _find_location_by_coords(location: str) -> int:
    """
    location: 'lat,lon' string.
    Uses /v3/locations?coordinates=lat,lon&radius=20000&limit=1
    Returns location ID or raises FetchError.
    """
    try:
        lat_str, lon_str = [p.strip() for p in location.split(",")]
        float(lat_str)
        float(lon_str)
    except Exception:
        raise FetchError(f"Invalid coordinate format: '{location}' (expected 'lat,lon')")

    params = {
        "coordinates": f"{lat_str},{lon_str}",
        "radius": 20000, 
        "limit": 1,
    }

    try:
        resp = requests.get(f"{BASE_URL}/locations", headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"Error fetching locations for coordinates {location}: {e}")

    results = (j or {}).get("results") or []
    if not results:
        raise FetchError(f"No OpenAQ locations found near coordinates {location}")

    return int(results[0]["id"])


def _find_location_by_name(city: str, iso: str = "IN") -> int:
    """
    Very simple resolver: pull locations for a country (iso) and fuzzy-match
    city name against 'name' and 'locality'.

    Returns first match ID or raises FetchError.
    """
    city_lower = city.strip().lower()
    if not city_lower:
        raise FetchError("Empty city name passed to _find_location_by_name")

    params = {
        "iso": iso,        
        "limit": 1000,     
        "page": 1,
    }

    try:
        resp = requests.get(f"{BASE_URL}/locations", headers=_headers(), params=params, timeout=15)
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"Error fetching locations for city '{city}': {e}")

    results = (j or {}).get("results") or []
    best_id: Optional[int] = None

    for loc in results:
        name = (loc.get("name") or "").lower()
        locality = (loc.get("locality") or "").lower()

        if city_lower in name or city_lower in locality:
            best_id = int(loc["id"])
            break

    if best_id is None:
        raise FetchError(f"No OpenAQ location found that matches city '{city}' (iso={iso})")

    return best_id


def _resolve_location_id(location: str, iso: str = "IN") -> int:
    """
    location:
      - 'CityName'  -> matches against locations in country iso
      - 'lat,lon'   -> matches nearest location by coords
    """
    if _is_lat_lon(location):
        return _find_location_by_coords(location)
    return _find_location_by_name(location, iso=iso)


def _get_pm25_sensor_ids_for_location(location_id: int) -> List[int]:
    """
    Uses /v3/locations/{id} and reads embedded sensors list.
    Filters sensors where parameter.id == 2 (pm25).
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/locations/{location_id}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"Error fetching location {location_id}: {e}")

    results = (j or {}).get("results") or []
    if not results:
        raise FetchError(f"Location {location_id} not found in OpenAQ")
    loc = results[0]
    sensors = loc.get("sensors") or []
    pm25_sensors: List[int] = []
    for s in sensors:
        param = s.get("parameter") or {}
        if int(param.get("id", -1)) == PM25_PARAMETER_ID or param.get("name") == "pm25":
            pm25_sensors.append(int(s["id"]))
    if not pm25_sensors:
        raise FetchError(f"No PM2.5 sensors found for location {location_id}")
    return pm25_sensors
def _fetch_monthly_pm25(sensor_id: int, datetime_from: str, datetime_to: str) -> List[Dict[str, Any]]:
    """
    Calls /v3/sensors/{sensor_id}/days/monthly for the given time range.
    Returns the raw 'results' list from the API.
    """
    url = f"{BASE_URL}/sensors/{sensor_id}/days/monthly"
    params = {
        "datetime_from": datetime_from,
        "datetime_to": datetime_to,
        "limit": 1000,  
        "page": 1,
    }
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=20)
        resp.raise_for_status()
        j = resp.json()
    except Exception as e:
        raise FetchError(f"Error fetching monthly PM2.5 for sensor {sensor_id}: {e}")
    results = (j or {}).get("results") or []
    return results
def history_aqi(location: str, months: int = 12, iso: str = "IN") -> List[Dict[str, Any]]:
    """
    Use OpenAQ v3 to get historical PM2.5 *monthly* stats for the last `months` months.

    - location: "CityName"  or  "lat,lon"
    - iso:      country code (default "IN" for India)

    Returns list of dicts like:
      {
        "month": "YYYY-MM",
        "avg_aqi": float | None,
        "peak_aqi": float | None,
        "least_aqi": float | None,
        "count": int,                  # number of daily values aggregated
      }
    NOTE: These are PM2.5 µg/m³ values, not an official AQI index.
    """
    dt_from, dt_to = _compute_datetime_range_iso(months)
    loc_id = _resolve_location_id(location, iso=iso)
    sensor_ids = _get_pm25_sensor_ids_for_location(loc_id)
    sensor_id = sensor_ids[0]
    results = _fetch_monthly_pm25(sensor_id, dt_from, dt_to)
    monthly: Dict[str, Dict[str, Any]] = {}
    for row in results:
        period = row.get("period") or {}
        dt_obj = (period.get("datetimeFrom") or {}).get("utc")
        if not dt_obj:
            coverage = row.get("coverage") or {}
            dt_obj = (coverage.get("datetimeFrom") or {}).get("utc")
        if not dt_obj:
            continue
        month_label = dt_obj[:7]
        summary = row.get("summary") or {}
        avg_val = int(summary.get("avg", row.get("value")))
        min_val = int(summary.get("min"))
        max_val = int(summary.get("max"))
        coverage = row.get("coverage") or {}
        count_val = int(coverage.get("observedCount"))
        monthly[month_label] = {
            "month": month_label,
            "avg_aqi": avg_val,
            "peak_aqi": max_val,
            "least_aqi": min_val,
            "count": count_val,
        }
    ordered_months = sorted(monthly.keys())
    return [monthly[m] for m in ordered_months]