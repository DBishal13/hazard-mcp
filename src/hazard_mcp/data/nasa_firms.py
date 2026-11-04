"""NASA FIRMS (Fire Information for Resource Management System) client.

https://firms.modaps.eosdis.nasa.gov/api/area/ -- near-real-time active
fire detections from MODIS/VIIRS. Unlike EONET (curated, human-verified
events), this is raw satellite hotspot detections -- higher volume, lower
latency. Requires a free MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/map_key/
"""

from __future__ import annotations

import csv
import io

import httpx

from hazard_mcp.cache import cached

from hazard_mcp.config import settings

BBox = tuple[float, float, float, float]
TIMEOUT = 30.0


class FirmsNotConfigured(RuntimeError):
    pass


@cached("nasa_firms")
def active_fires(bbox: BBox, source: str = "VIIRS_SNPP_NRT", days: int = 1) -> list[dict]:
    """Active fire detections (satellite hotspots) intersecting bbox in the
    last `days` days (1-10).

    Raises FirmsNotConfigured if HAZARD_MCP_FIRMS_MAP_KEY isn't set --
    get a free key at https://firms.modaps.eosdis.nasa.gov/api/map_key/
    """
    if not settings.firms_map_key:
        raise FirmsNotConfigured(
            "NASA FIRMS requires a free API key. Register at "
            "https://firms.modaps.eosdis.nasa.gov/api/map_key/ and set "
            "HAZARD_MCP_FIRMS_MAP_KEY (env var or .env file)."
        )

    min_lon, min_lat, max_lon, max_lat = bbox
    area = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    url = f"{settings.firms_base_url}/{settings.firms_map_key}/{source}/{area}/{days}"

    resp = httpx.get(url, timeout=TIMEOUT)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    results = []
    for row in reader:
        results.append(
            {
                "lat": float(row["latitude"]),
                "lon": float(row["longitude"]),
                "brightness_k": float(row.get("bright_ti4", row.get("brightness", 0)) or 0),
                "confidence": row.get("confidence"),
                "date": row.get("acq_date"),
                "time": row.get("acq_time"),
                "satellite": row.get("satellite"),
                "frp_mw": float(row["frp"]) if row.get("frp") else None,
            }
        )
    return results


if __name__ == "__main__":
    try:
        fires = active_fires((-125.0, 32.0, -114.0, 42.0), days=1)
        print(f"{len(fires)} active fire detections in California, last 24h")
        for f in fires[:5]:
            print(" ", f["date"], f["lat"], f["lon"], f"{f['frp_mw']} MW")
    except FirmsNotConfigured as e:
        print(f"Skipped (expected without a key): {e}")
