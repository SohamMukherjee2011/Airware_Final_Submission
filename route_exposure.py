from typing import List, Dict
from realtime_aqi import realtime_aqi
from exceptions import FetchError

def calculate_exposure(route_points: List[Dict[str, float]]) -> Dict[str, float]:
    """
    route_points: [{'lat': 22.5, 'lon': 88.3}, ...] OR [{'lat':.., 'lng':..}]
    Returns:
      {
        "avg_aqi": float,
        "max_aqi": int,
        "min_aqi": int,
        "exposure_score": float  # normalized 0-100 (simple scaling)
      }
    """
    aqi_values = []
    for p in route_points:
        lat = p.get("lat")
        lon = p.get("lon") 
        if lat is None or lon is None:
            continue
        loc = f"{lat},{lon}"
        try:
            aqi = realtime_aqi(loc)
            aqi_values.append(int(aqi))
        except Exception:
            # skip points we can't fetch
            continue

    if len(aqi_values) == 0:
        raise FetchError("No AQI data available for any route points")

    avg = sum(aqi_values) / len(aqi_values)
    mx = max(aqi_values)
    mn = min(aqi_values)

    # simple exposure score: map avg aqi to 0-100 (0..50 => low, 50..100 moderate..)
    exposure_score = min(100.0, max(0.0, (avg / 500.0) * 100.0))
    return {
        "avg_aqi": avg,
        "max_aqi": mx,
        "min_aqi": mn,
        "exposure_score": exposure_score
    }