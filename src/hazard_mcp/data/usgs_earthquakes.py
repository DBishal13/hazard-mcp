"""USGS earthquake catalog client.

https://earthquake.usgs.gov/fdsnws/event/1/ -- no API key needed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from hazard_mcp.cache import cached

from hazard_mcp.config import settings

BBox = tuple[float, float, float, float]
TIMEOUT = 30.0


@cached("usgs_earthquakes")
def earthquakes(
    bbox: BBox,
    min_magnitude: float = 2.5,
    days: int = 30,
) -> list[dict]:
    """Earthquakes intersecting bbox in the last `days` days, as a list of
    {id, magnitude, place, time, lon, lat, depth_km, url}."""
    min_lon, min_lat, max_lon, max_lat = bbox
    starttime = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "format": "geojson",
        "minlongitude": min_lon,
        "minlatitude": min_lat,
        "maxlongitude": max_lon,
        "maxlatitude": max_lat,
        "minmagnitude": min_magnitude,
        "starttime": starttime,
        "orderby": "time",
    }
    resp = httpx.get(settings.usgs_earthquake_base_url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    features = resp.json().get("features", [])

    results = []
    for f in features:
        props = f["properties"]
        lon, lat, depth_km = f["geometry"]["coordinates"]
        results.append(
            {
                "id": f["id"],
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "time": datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc).isoformat(),
                "lon": lon,
                "lat": lat,
                "depth_km": depth_km,
                "url": props.get("url"),
            }
        )
    return results


if __name__ == "__main__":
    # California bbox
    quakes = earthquakes((-125.0, 32.0, -114.0, 42.0), min_magnitude=3.0, days=30)
    print(f"{len(quakes)} earthquakes M3.0+ in California, last 30 days")
    for q in quakes[:5]:
        print(" ", q["time"][:10], f"M{q['magnitude']}", q["place"])
