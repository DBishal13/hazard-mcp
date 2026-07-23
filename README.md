# HazardMCP — Unified Multi-Hazard Disaster-Intelligence MCP Server

## Description
An MCP server (Python, FastMCP) that unifies multiple US hazard APIs behind a single
agent-facing interface: OpenFEMA disaster declarations + NFIP claims, USGS earthquake
GeoJSON feeds, NOAA NWPS river/flood forecasts and flood-inundation maps, NWS weather
alerts, and NASA EONET/FIRMS fire events. Includes a `render_map` tool (Folium/leafmap)
and a location-risk-summary tool that geocodes an address and returns all active hazards
nearby.

## Why it stands out
Disaster-data MCPs today are fragmented across separate single-source servers (cyanheads'
OpenFEMA, earthquake, NWS servers). No server unifies multi-hazard feeds with map output,
and NOAA NWPS has no dedicated MCP wrapper at all. This is genuine white space that
showcases MCP, API/data-engineering, and geospatial skills at once.

## Open data
- OpenFEMA API
- USGS earthquake GeoJSON
- NOAA NWPS API (api.water.noaa.gov)
- NWS weather alerts
- NASA EONET + FIRMS

## Tech stack
Python, FastMCP/MCP SDK, FastAPI (optional HTTP transport + demo UI), DuckDB
(caching/spatial joins), Folium/leafmap, deployed on AWS (ECS/Lambda) or Render.

## Status
Not started.
