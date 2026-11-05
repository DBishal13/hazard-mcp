"""HazardMCP: a unified multi-hazard disaster-intelligence MCP server.

Wraps OpenFEMA, USGS earthquakes, NWS alerts, NASA EONET/FIRMS, and NOAA
NWPS behind one agent-facing interface, plus a location_risk_summary tool
that geocodes a place and pulls every hazard source for the surrounding
area, and a render_map tool for combined visual output.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP

from hazard_mcp.config import settings
from hazard_mcp.data import geocode as geocode_client
from hazard_mcp.data import (
    nasa_eonet,
    nasa_firms,
    nwps,
    nws_alerts,
    openfema,
    usgs_earthquakes,
)
from hazard_mcp.data.nasa_firms import FirmsNotConfigured
from hazard_mcp.mapping import render_map as _render_map

mcp = FastMCP(
    "hazard-mcp",
    instructions=(
        "Unified US multi-hazard disaster intelligence: FEMA disaster "
        "declarations, NFIP flood claims, USGS earthquakes, NWS weather "
        "alerts, NASA wildfire events (EONET) and active fire detections "
        "(FIRMS), and NOAA river gauges / flood-inundation extent. Use "
        "location_risk_summary for a one-call overview of a place, or the "
        "individual get_* tools for source-specific queries."
    ),
)


@mcp.tool()
def geocode(query: str) -> dict:
    """Resolve a free-text place name (e.g. 'Naples, FL') to lat/lon."""
    return geocode_client.geocode(query)


@mcp.tool()
def get_disaster_declarations(state: str | None = None, incident_type: str | None = None, limit: int = 20) -> list[dict]:
    """FEMA disaster declarations, optionally filtered by 2-letter state
    code and/or incident type (e.g. 'Hurricane', 'Flood', 'Fire')."""
    return openfema.disaster_declarations(state, incident_type, limit)


@mcp.tool()
def get_nfip_claims(state: str | None = None, county: str | None = None, limit: int = 20) -> list[dict]:
    """Redacted NFIP flood insurance claims, optionally filtered by
    2-letter state code and/or county."""
    return openfema.nfip_claims(state, county, limit)


@mcp.tool()
def get_earthquakes(min_lon: float, min_lat: float, max_lon: float, max_lat: float, min_magnitude: float = 2.5, days: int = 30) -> list[dict]:
    """USGS earthquakes within a bounding box in the last `days` days."""
    return usgs_earthquakes.earthquakes((min_lon, min_lat, max_lon, max_lat), min_magnitude, days)


@mcp.tool()
def get_weather_alerts(lat: float, lon: float) -> list[dict]:
    """Active NWS weather alerts (severe storms, flood, fire weather, red
    flag warnings, ...) covering the given point."""
    return nws_alerts.active_alerts_near(lat, lon)


@mcp.tool()
def get_wildfire_events(min_lon: float, min_lat: float, max_lon: float, max_lat: float, days: int = 20) -> list[dict]:
    """NASA EONET curated wildfire events within a bounding box."""
    return nasa_eonet.events((min_lon, min_lat, max_lon, max_lat), category="wildfires", days=days)


@mcp.tool()
def get_active_fires(min_lon: float, min_lat: float, max_lon: float, max_lat: float, days: int = 1) -> list[dict] | dict:
    """NASA FIRMS raw satellite fire-hotspot detections within a bounding
    box (last 1-10 days). Requires a free API key -- returns an
    explanatory dict instead of raising if one isn't configured."""
    try:
        return nasa_firms.active_fires((min_lon, min_lat, max_lon, max_lat), days=days)
    except FirmsNotConfigured as e:
        return {"error": str(e)}


@mcp.tool()
def get_river_gauges(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> list[dict]:
    """NOAA NWPS river gauges within a bounding box."""
    return nwps.gauges_in_bbox((min_lon, min_lat, max_lon, max_lat))


@mcp.tool()
def get_flood_inundation_extent(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> list[dict]:
    """Live NOAA NWM flood-inundation extent polygons within a bounding
    box. Empty outside an active flood event -- that's the common case."""
    return nwps.flood_inundation_extent((min_lon, min_lat, max_lon, max_lat))


@mcp.tool()
def location_risk_summary(place: str, radius_km: float = 50) -> dict:
    """Geocode `place` and pull every hazard source for the surrounding
    radius_km: recent disaster declarations, active weather alerts,
    earthquakes, wildfires, active fire detections, river gauges, and any
    active flood-inundation extent. One-call overview for 'what's the
    hazard picture around X'."""
    loc = geocode_client.geocode(place)
    bbox = geocode_client.bbox_around(loc["lat"], loc["lon"], radius_km)

    result: dict = {"location": loc, "bbox": list(bbox), "radius_km": radius_km}

    # Seven independent upstream APIs: fetch them concurrently, and let one
    # failing (rate limit, outage, missing FIRMS key) degrade to an error
    # entry instead of sinking the whole summary.
    sources = {
        "disaster_declarations": lambda: openfema.disaster_declarations(limit=10),
        "weather_alerts": lambda: nws_alerts.active_alerts_near(loc["lat"], loc["lon"]),
        "earthquakes": lambda: usgs_earthquakes.earthquakes(bbox, min_magnitude=2.5, days=30),
        "wildfire_events": lambda: nasa_eonet.events(bbox, category="wildfires", days=20),
        "river_gauges": lambda: nwps.gauges_in_bbox(bbox),
        "flood_inundation_extent": lambda: nwps.flood_inundation_extent(bbox),
        "active_fires": lambda: nasa_firms.active_fires(bbox, days=1),
    }
    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futures = {name: pool.submit(fn) for name, fn in sources.items()}
    for name, fut in futures.items():
        try:
            result[name] = fut.result()
        except FirmsNotConfigured as e:
            result[name] = {"error": str(e)}
        except Exception as e:  # noqa: BLE001 -- surface, don't crash
            result[name] = {"error": f"{type(e).__name__}: {e}"}

    return result


def _items(summary: dict, key: str) -> list:
    """A source's results, or [] if it's missing or degraded to {"error": ...}."""
    v = summary.get(key)
    return v if isinstance(v, list) else []


@mcp.tool()
def render_hazard_map(summary: dict) -> dict:
    """Render a combined map from a location_risk_summary() result (or a
    hand-built dict with the same shape). Returns the path to a saved
    standalone HTML map."""
    features = []
    loc = summary.get("location", {})

    for eq in _items(summary, "earthquakes"):
        features.append({"category": "earthquake", "lat": eq.get("lat"), "lon": eq.get("lon"), "label": eq.get("place"), "detail": f"M{eq.get('magnitude')}"})
    for ev in _items(summary, "wildfire_events"):
        features.append({"category": "wildfire", "lat": ev.get("lat"), "lon": ev.get("lon"), "label": ev.get("title")})
    for f in _items(summary, "active_fires"):
        if isinstance(f, dict) and "lat" in f:
            features.append({"category": "wildfire", "lat": f.get("lat"), "lon": f.get("lon"), "label": "Active fire detection", "detail": f"{f.get('frp_mw')} MW"})
    for g in _items(summary, "river_gauges"):
        loc_g = (g.get("location") or {}).get("point") or {}
        features.append({"category": "river_gauge", "lat": loc_g.get("latitude"), "lon": loc_g.get("longitude"), "label": g.get("name")})
    for extent in _items(summary, "flood_inundation_extent"):
        geom = extent.get("geometry", {})
        rings = geom.get("rings") or geom.get("coordinates")
        if rings:
            ring = rings[0]
            lon, lat = ring[0][0], ring[0][1]
            features.append({"category": "flood", "lat": lat, "lon": lon, "label": "Active flood-inundation extent"})

    center = (loc.get("lat"), loc.get("lon")) if loc.get("lat") is not None else None
    path = _render_map(features, center=center)
    out = {"map_path": path, "feature_count": len(features)}
    # Over HTTP the caller can't open a file on the server, so hand back a
    # link that re-renders the same map from the public demo.
    if settings.public_url and center:
        params = urlencode({"lat": center[0], "lon": center[1], "radius_km": summary.get("radius_km", 50)})
        out["map_url"] = f"{settings.public_url.rstrip('/')}/api/map?{params}"
    return out


def main() -> None:
    """`hazard-mcp` (stdio, for a local MCP host) or `hazard-mcp --http`
    (streamable HTTP + demo page on :8000, same app that runs on Vercel)."""
    if "--http" in sys.argv[1:]:
        import uvicorn

        from hazard_mcp.web import app

        uvicorn.run(app, host="0.0.0.0", port=settings.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
