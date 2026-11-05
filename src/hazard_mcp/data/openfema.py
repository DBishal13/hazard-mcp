"""OpenFEMA API client: disaster declarations + NFIP redacted claims.

https://www.fema.gov/about/openfema/api -- OData-style query params
($filter, $top, $orderby, $select) over JSON datasets, no API key needed.
"""

from __future__ import annotations

import httpx

from hazard_mcp.cache import cached
from hazard_mcp.config import settings

TIMEOUT = 30.0


@cached("openfema_declarations")
def disaster_declarations(
    state: str | None = None,
    incident_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Recent FEMA disaster declarations, optionally filtered by state
    (2-letter code) and/or incident type (e.g. 'Hurricane', 'Flood')."""
    filters = []
    if state:
        filters.append(f"state eq '{state.upper()}'")
    if incident_type:
        filters.append(f"incidentType eq '{incident_type}'")

    params = {
        "$top": limit,
        "$orderby": "declarationDate desc",
        "$format": "json",
    }
    if filters:
        params["$filter"] = " and ".join(filters)

    resp = httpx.get(
        f"{settings.openfema_base_url}/v2/DisasterDeclarationsSummaries",
        params=params,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("DisasterDeclarationsSummaries", [])


@cached("openfema_nfip")
def nfip_claims(
    state: str | None = None,
    county: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Redacted NFIP (National Flood Insurance Program) claims, optionally
    filtered by state (2-letter code) and/or county name."""
    filters = []
    if state:
        filters.append(f"state eq '{state.upper()}'")
    if county:
        filters.append(f"countyCode eq '{county}'")

    params = {
        "$top": limit,
        "$orderby": "dateOfLoss desc",
        "$format": "json",
    }
    if filters:
        params["$filter"] = " and ".join(filters)

    resp = httpx.get(
        f"{settings.openfema_base_url}/v3/NfipClaims",
        params=params,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json().get("NfipClaims", [])


if __name__ == "__main__":
    declarations = disaster_declarations(state="FL", limit=5)
    print(f"{len(declarations)} FL disaster declarations")
    for d in declarations:
        print(" ", d["declarationDate"][:10], d["incidentType"], d["declarationTitle"])

    claims = nfip_claims(state="FL", limit=3)
    print(f"\n{len(claims)} FL NFIP claims")
    for c in claims:
        print(" ", c.get("dateOfLoss", "")[:10], c.get("ratedFloodZone"), c.get("amountPaidOnBuildingClaim"))
