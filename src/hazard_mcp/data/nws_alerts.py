"""NWS (National Weather Service) active alerts client.

https://api.weather.gov -- no API key, but a descriptive User-Agent header
is required (see config.USER_AGENT).
"""

from __future__ import annotations

import httpx

from hazard_mcp.cache import cached
from hazard_mcp.config import USER_AGENT, settings

TIMEOUT = 30.0


@cached("nws_alerts")
def active_alerts_near(lat: float, lon: float) -> list[dict]:
    """Active NWS alerts (severe weather, flood, fire weather, etc.)
    covering the given point."""
    resp = httpx.get(
        f"{settings.nws_base_url}/alerts/active",
        params={"point": f"{lat},{lon}"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return _extract(resp.json())


@cached("nws_alerts")
def active_alerts_in_state(state: str) -> list[dict]:
    """Active NWS alerts for a 2-letter state code."""
    resp = httpx.get(
        f"{settings.nws_base_url}/alerts/active",
        params={"area": state.upper()},
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return _extract(resp.json())


def _extract(geojson: dict) -> list[dict]:
    results = []
    for f in geojson.get("features", []):
        p = f["properties"]
        results.append(
            {
                "id": p.get("id"),
                "event": p.get("event"),
                "severity": p.get("severity"),
                "certainty": p.get("certainty"),
                "urgency": p.get("urgency"),
                "headline": p.get("headline"),
                "area_desc": p.get("areaDesc"),
                "effective": p.get("effective"),
                "expires": p.get("expires"),
            }
        )
    return results


if __name__ == "__main__":
    alerts = active_alerts_in_state("FL")
    print(f"{len(alerts)} active alerts in FL")
    for a in alerts[:5]:
        print(" ", a["severity"], a["event"], "-", a["area_desc"])
