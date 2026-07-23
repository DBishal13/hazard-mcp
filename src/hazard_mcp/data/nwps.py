"""NOAA National Water Prediction Service (NWPS) client: river gauges,
streamflow forecasts, and live flood-inundation extent polygons.

https://api.water.noaa.gov/nwps/v1 -- official streamflow forecasts and
gauge observations. Flood-inundation-mapping (FIM) polygons are a separate
ArcGIS REST service on NOAA's HydroVIS platform (maps.water.noaa.gov).
"""

from __future__ import annotations

import httpx

from hazard_mcp.config import settings

BBox = tuple[float, float, float, float]
TIMEOUT = 30.0


def gauges_in_bbox(bbox: BBox, catfim: bool = False) -> list[dict]:
    """River gauge metadata within bbox."""
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "bbox.xmin": min_lon,
        "bbox.ymin": min_lat,
        "bbox.xmax": max_lon,
        "bbox.ymax": max_lat,
        "srid": "EPSG_4326",
    }
    if catfim:
        params["catfim"] = "true"
    resp = httpx.get(f"{settings.nwps_base_url}/gauges", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("gauges", [])


def gauge_stageflow(identifier: str) -> dict:
    """Observed + forecast stage/flow for a single gauge (LID or USGS ID)."""
    resp = httpx.get(f"{settings.nwps_base_url}/gauges/{identifier}/stageflow", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def flood_inundation_extent(bbox: BBox, layer: int = 0) -> list[dict]:
    """Live NWM analysis-and-assimilation flood-inundation extent polygons
    intersecting bbox, as [{geometry: <geojson geometry>, attributes: {...}}].
    Empty outside an active flood event -- the common case."""
    min_lon, min_lat, max_lon, max_lat = bbox
    resp = httpx.get(
        f"{settings.nwm_fim_base_url}/{layer}/query",
        params={
            "where": "1=1",
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    features = resp.json().get("features", [])
    return [{"geometry": f["geometry"], "attributes": f["properties"]} for f in features]


if __name__ == "__main__":
    # South Florida bbox
    bbox = (-80.60, 25.40, -80.00, 26.20)
    gauges = gauges_in_bbox(bbox)
    print(f"{len(gauges)} NWPS gauges in South Florida bbox")
    for g in gauges[:5]:
        print(" ", g.get("lid"), g.get("name"))

    extent = flood_inundation_extent(bbox)
    print(f"\n{len(extent)} active flood-inundation polygons in bbox (0 is normal/expected)")
