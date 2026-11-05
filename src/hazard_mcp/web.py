"""HTTP face of hazard-mcp: the MCP server over streamable HTTP at /mcp,
plus a small public demo (landing page and two JSON/HTML endpoints) so the
project can be tried without installing an MCP host.

Run locally with `hazard-mcp --http`; on Vercel, api/index.py imports `app`.

The MCP endpoint is stateless (no session affinity), which is what a
serverless host needs: any instance can answer any request.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response

from hazard_mcp.server import location_risk_summary, mcp, render_hazard_map

MAX_RADIUS_KM = 150  # keep public-demo queries to a sane area
STATIC = Path(__file__).parent / "static"

mcp.settings.stateless_http = True
mcp.settings.json_response = True
# Behind Vercel's proxy the Host header is the public domain, not localhost;
# DNS-rebinding protection only matters for servers bound to a local port
# in a user's browser, which this deployment isn't.
mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _radius(request: Request) -> float:
    try:
        r = float(request.query_params.get("radius_km", 50))
    except ValueError:
        r = 50.0
    return max(1.0, min(r, MAX_RADIUS_KM))


def _error(msg: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": msg}, status_code=status)


@mcp.custom_route("/", methods=["GET"])
async def index(request: Request) -> Response:
    return HTMLResponse((STATIC / "index.html").read_text())


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"ok": True})


@mcp.custom_route("/api/summary", methods=["GET"])
async def api_summary(request: Request) -> Response:
    place = (request.query_params.get("place") or "").strip()
    if not place:
        return _error("Pass ?place=, e.g. ?place=Naples, FL")
    if len(place) > 120:
        return _error("place is too long")
    try:
        return JSONResponse(location_risk_summary(place, _radius(request)))
    except ValueError as e:  # geocode miss
        return _error(str(e), 404)
    except Exception as e:  # noqa: BLE001
        return _error(f"Upstream lookup failed: {type(e).__name__}", 502)


@mcp.custom_route("/api/map", methods=["GET"])
async def api_map(request: Request) -> Response:
    """Interactive hazard map. ?place=... or ?lat=..&lon=.. (the form the
    render_hazard_map tool links to)."""
    q = request.query_params
    radius = _radius(request)
    try:
        if q.get("lat") and q.get("lon"):
            lat, lon = float(q["lat"]), float(q["lon"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                return _error("lat/lon out of range")
            # Reverse-geocoding isn't needed: the summary only uses the
            # point, so feed it straight through as a coordinate string.
            summary = location_risk_summary(f"{lat},{lon}", radius)
        elif q.get("place"):
            summary = location_risk_summary(q["place"].strip()[:120], radius)
        else:
            return _error("Pass ?place= or ?lat=&lon=")
    except ValueError as e:
        return _error(str(e), 404)
    except Exception as e:  # noqa: BLE001
        return _error(f"Upstream lookup failed: {type(e).__name__}", 502)

    path = render_hazard_map(summary)["map_path"]
    try:
        html = Path(path).read_text()
    finally:
        Path(path).unlink(missing_ok=True)  # don't fill /tmp on a warm instance
    return HTMLResponse(html)


app = mcp.streamable_http_app()

__all__ = ["app"]
