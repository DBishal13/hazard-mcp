from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

USER_AGENT = "hazard-mcp/0.1 (personal portfolio project)"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HAZARD_MCP_", env_file=".env")

    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "data" / "maps"

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
