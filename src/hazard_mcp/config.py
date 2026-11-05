import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

USER_AGENT = "hazard-mcp/0.1 (personal portfolio project)"

# Serverless hosts (Vercel) only allow writes under /tmp.
_DATA_ROOT = Path("/tmp/hazard-mcp") if os.environ.get("VERCEL") else PROJECT_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAZARD_MCP_", env_file=".env")

    data_dir: Path = _DATA_ROOT
    output_dir: Path = _DATA_ROOT / "maps"
    cache_dir: Path = _DATA_ROOT / "cache"
    # Set HAZARD_MCP_CACHE_ENABLED=false to always hit the live APIs.
    cache_enabled: bool = True

    # HTTP mode: public base URL of the deployment (for map links) and port.
    public_url: str | None = None
    port: int = 8000

    openfema_base_url: str = "https://www.fema.gov/api/open"
    usgs_earthquake_base_url: str = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    nws_base_url: str = "https://api.weather.gov"
    eonet_base_url: str = "https://eonet.gsfc.nasa.gov/api/v3/events"
    nwps_base_url: str = "https://api.water.noaa.gov/nwps/v1"
    nwm_fim_base_url: str = "https://maps.water.noaa.gov/server/rest/services/nwm/ana_inundation_extent/MapServer"

    # Free registration: https://firms.modaps.eosdis.nasa.gov/api/map_key/
    firms_map_key: str | None = None
    firms_base_url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


settings = Settings()
