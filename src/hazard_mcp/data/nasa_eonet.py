"""NASA EONET (Earth Observatory Natural Event Tracker) client.

https://eonet.gsfc.nasa.gov/docs/v3 -- curated natural events (wildfires,
severe storms, volcanoes, floods, ...), no API key needed.
"""

from __future__ import annotations

import httpx

from hazard_mcp.cache import cached
from hazard_mcp.config import settings

BBox = tuple[float, float, float, float]
TIMEOUT = 30.0


@cached("nasa_eonet")
def events(
    bbox: BBox | None = None,
    category: str | None = None,
    days: int = 20,
    status: str = "open",
) -> list[dict]:
    """Natural events (category e.g. 'wildfires', 'severeStorms',
    'volcanoes', 'floods'; omit for all categories).

    bbox: (min_lon, min_lat, max_lon, max_lat) -- EONET's own bbox param
    order is (min_lon, max_lat, max_lon, min_lat), reordered here.
    """
    params: dict = {"status": status, "days": days}
    if category:
        params["category"] = category
    if bbox:
        min_lon, min_lat, max_lon, max_lat = bbox
        params["bbox"] = f"{min_lon},{max_lat},{max_lon},{min_lat}"

    resp = httpx.get(settings.eonet_base_url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    raw_events = resp.json().get("events", [])

    results = []
    for e in raw_events:
        geometries = e.get("geometry", [])
        latest = geometries[-1] if geometries else {}
        coords = latest.get("coordinates")
        results.append(
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "categories": [c["title"] for c in e.get("categories", [])],
                "date": latest.get("date"),
                "lon": coords[0] if coords else None,
                "lat": coords[1] if coords else None,
                "sources": [s.get("url") for s in e.get("sources", [])],
            }
        )
    return results


if __name__ == "__main__":
    fires = events(category="wildfires", days=20)
    print(f"{len(fires)} open wildfire events (last 20 days)")
    for f in fires[:5]:
        print(" ", f["date"], f["title"])
