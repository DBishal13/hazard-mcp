"""HTTP layer tests. Upstream APIs are stubbed so these run offline."""

import pytest
from starlette.testclient import TestClient

from hazard_mcp import server, web
from hazard_mcp.data import geocode


@pytest.fixture(scope="module")
def _app_client():
    # The MCP session manager can only be started once per app instance,
    # so share one client (and its lifespan) across the module.
    with TestClient(web.app) as c:
        yield c


@pytest.fixture
def client(_app_client, monkeypatch, tmp_path):
    from hazard_mcp.config import settings

    monkeypatch.setattr(settings, "cache_enabled", False)
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    monkeypatch.setattr(geocode, "_geocode_place", lambda q: {"lat": 26.14, "lon": -81.79, "display_name": q})
    monkeypatch.setattr(server.openfema, "disaster_declarations", lambda **kw: [{"id": 1}])
    monkeypatch.setattr(server.nws_alerts, "active_alerts_near", lambda lat, lon: [])
    monkeypatch.setattr(server.usgs_earthquakes, "earthquakes", lambda *a, **kw: [{"lat": 26.2, "lon": -81.8, "place": "x", "magnitude": 2.6}])
    monkeypatch.setattr(server.nasa_eonet, "events", lambda *a, **kw: [])
    monkeypatch.setattr(server.nwps, "gauges_in_bbox", lambda *a, **kw: [])

    def boom(*a, **kw):
        raise RuntimeError("upstream 503")

    monkeypatch.setattr(server.nwps, "flood_inundation_extent", boom)
    # FIRMS left as-is: no key configured -> FirmsNotConfigured, no network.
    monkeypatch.setattr(settings, "firms_map_key", None)
    return _app_client


def test_landing_page(client):
    r = client.get("/")
    assert r.status_code == 200 and "hazard-mcp" in r.text


def test_summary_degrades_per_source(client):
    d = client.get("/api/summary", params={"place": "Naples, FL", "radius_km": 9999}).json()
    assert d["radius_km"] == web.MAX_RADIUS_KM  # clamped
    assert d["disaster_declarations"] == [{"id": 1}]
    assert "RuntimeError" in d["flood_inundation_extent"]["error"]
    assert "API key" in d["active_fires"]["error"]


def test_summary_requires_place(client):
    assert client.get("/api/summary").status_code == 400


def test_map_by_latlon_skips_geocoder(client, monkeypatch):
    monkeypatch.setattr(geocode, "_geocode_place", lambda q: pytest.fail("should not geocode"))
    r = client.get("/api/map", params={"lat": 26.14, "lon": -81.79})
    assert r.status_code == 200 and "leaflet" in r.text.lower()


def test_map_rejects_bad_coords(client):
    assert client.get("/api/map", params={"lat": 200, "lon": 0}).status_code == 400


def test_mcp_endpoint_lists_tools(client):
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
    assert client.post("/mcp", json=init, headers=headers).status_code == 200
    r = client.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, headers=headers)
    names = {t["name"] for t in r.json()["result"]["tools"]}
    assert {"location_risk_summary", "render_hazard_map", "get_earthquakes"} <= names
