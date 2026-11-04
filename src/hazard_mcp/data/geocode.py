"""Address -> lat/lon via OpenStreetMap Nominatim (free, no API key)."""

from __future__ import annotations

import re

import httpx

from hazard_mcp.cache import cached
from hazard_mcp.config import USER_AGENT

TIMEOUT = 10.0


_LATLON = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def geocode(query: str) -> dict:
    """Resolve a free-text place name (or a literal 'lat,lon') to
    {lat, lon, display_name}."""
    m = _LATLON.match(query)
    if m:
        lat, lon = float(m[1]), float(m[2])
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return {"lat": lat, "lon": lon, "display_name": f"{lat:.4f}, {lon:.4f}"}
    return _geocode_place(query)


@cached("geocode")
def _geocode_place(query: str) -> dict:
    resp = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"No location found for '{query}'")
    r = results[0]
    return {
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "display_name": r["display_name"],
    }


def bbox_around(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Rough bbox around a point -- 1 deg latitude ~= 111km; longitude
    degree width shrinks with latitude, approximated via cos(lat)."""
    import math

    lat_span = radius_km / 111.0
    lon_span = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.1))
    return (lon - lon_span, lat - lat_span, lon + lon_span, lat + lat_span)


if __name__ == "__main__":
    loc = geocode("Key West, FL")
    print(loc)
    print(bbox_around(loc["lat"], loc["lon"], 50))
