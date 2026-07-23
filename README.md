# HazardMCP — Unified Multi-Hazard Disaster-Intelligence MCP Server

## Description
An MCP server (Python, FastMCP) that unifies multiple US hazard APIs behind a single
agent-facing interface: OpenFEMA disaster declarations + NFIP claims, USGS earthquake
GeoJSON feeds, NOAA NWPS river gauges + live flood-inundation extent, NWS weather
alerts, and NASA EONET wildfire events + FIRMS fire detections. A `location_risk_summary`
tool geocodes a place and pulls every source for the surrounding area in one call; a
`render_hazard_map` tool renders the combined result to a standalone HTML map (Folium).

## Why it stands out
Disaster-data MCPs today are fragmented across separate single-source servers. No
server unifies multi-hazard feeds with map output, and NOAA NWPS has no dedicated MCP
wrapper at all. This is genuine white space that showcases MCP, API/data-engineering,
and geospatial skills at once.

## Tools
| Tool | Source |
|---|---|
| `geocode` | OpenStreetMap Nominatim |
| `get_disaster_declarations` | OpenFEMA |
| `get_nfip_claims` | OpenFEMA (NFIP redacted claims v3) |
| `get_earthquakes` | USGS earthquake catalog |
| `get_weather_alerts` | NWS active alerts |
| `get_wildfire_events` | NASA EONET (curated events) |
| `get_active_fires` | NASA FIRMS (raw satellite hotspots — needs a free API key) |
| `get_river_gauges` | NOAA NWPS |
| `get_flood_inundation_extent` | NOAA NWM (live FIM polygons, HydroVIS ArcGIS service) |
| `location_risk_summary` | all of the above, one call |
| `render_hazard_map` | renders a `location_risk_summary` result to HTML |

## Setup
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

NASA FIRMS is the only source needing a credential — everything else is keyless.
Register for a free MAP_KEY at https://firms.modaps.eosdis.nasa.gov/api/map_key/,
then set it via env var or a `.env` file:
```
HAZARD_MCP_FIRMS_MAP_KEY=your_key_here
```
Without it, `get_active_fires` / `location_risk_summary` return an explanatory error
for that source instead of failing — every other tool works fine unconfigured.

## Run
Stdio transport (the MCP default — an agent host spawns the process and talks over
stdin/stdout):
```bash
python -m hazard_mcp.server
```

To try it interactively with the MCP Inspector:
```bash
mcp dev src/hazard_mcp/server.py
```

To use it from Claude Desktop (or another MCP host), add to its config:
```json
{
  "mcpServers": {
    "hazard-mcp": {
      "command": "/absolute/path/to/hazard-mcp/.venv/bin/python",
      "args": ["-m", "hazard_mcp.server"]
    }
  }
}
```

## Run with Docker
```bash
docker build -t hazard-mcp .
docker run -i --rm -v hazard-mcp-data:/app/data hazard-mcp
```
(`-i` is required — MCP stdio transport needs an attached stdin.)

## Architecture
- `data/openfema.py` — FEMA disaster declarations + NFIP claims (OData-style query API).
- `data/usgs_earthquakes.py` — USGS earthquake catalog (GeoJSON feed).
- `data/nws_alerts.py` — NWS active alerts by point or state.
- `data/nasa_eonet.py` — curated natural events (wildfires, storms, ...).
- `data/nasa_firms.py` — raw satellite fire-hotspot detections (needs API key).
- `data/nwps.py` — NOAA river gauges + live NWM flood-inundation extent polygons.
- `data/geocode.py` — place name → lat/lon (Nominatim) + radius → bbox helper.
- `mapping.py` — combined-hazard Folium map, hazard type as a fixed-order categorical
  color (identity, not severity — matches the dataviz skill's categorical-vs-ordinal rule).
- `server.py` — FastMCP server wiring all of the above as tools.

## Tests
```bash
pytest tests/
```
Unit tests cover map rendering and bbox math offline. Each `data/*.py` module also has
a `python -m hazard_mcp.data.<module>` smoke test that hits the real live API directly
(useful for manually re-verifying a source still works as documented) — not run in CI.

## Status
Working: all 9 hazard/geocode/summary tools verified against real live APIs and through
the actual MCP protocol layer (tool discovery + `call_tool`), not just direct Python
calls. Demo-verified against Naples, FL (`location_risk_summary` pulled 10 disaster
declarations, 36 river gauges, and rendered a combined map in one call).

## Next steps
- Deploy behind a live demo (HTTP/SSE transport + a small landing page, similar to the
  surge-exposure project) so it's usable without a local MCP host.
- Cache hazard responses (same disk-cache pattern as surge-exposure) to make
  `location_risk_summary` cheaper on repeat calls for the same area.
- Publish a standalone NWPS API client to PyPI (none exists yet, per the original
  research — reusable across this and the surge-exposure project).
