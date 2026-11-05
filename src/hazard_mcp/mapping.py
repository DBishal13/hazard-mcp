"""Render a unified hazard map (Folium) from mixed-source hazard features.

Hazard type is an identity distinction (which kind of hazard, not a
magnitude), so it's encoded with the fixed-order categorical palette
rather than a severity ramp -- swapping two hazard types' colors wouldn't
change their meaning, unlike an ordered risk tier.
"""

from __future__ import annotations

import time
import uuid

import folium

from hazard_mcp.config import settings

# Categorical palette, fixed order (see dataviz skill: color-formula.md).
CATEGORY_COLOR = {
    "earthquake": "#2a78d6",  # slot 1 blue
    "wildfire": "#eb6834",  # slot 2 orange
    "flood": "#1baf7a",  # slot 3 aqua
    "weather_alert": "#eda100",  # slot 4 yellow
    "disaster_declaration": "#e87ba4",  # slot 5 magenta
    "river_gauge": "#008300",  # slot 6 green
}
DEFAULT_COLOR = "#52514e"  # muted -- unrecognized category


def render_map(features: list[dict], center: tuple[float, float] | None = None) -> str:
    """features: list of {category, lat, lon, label, detail (optional)}.
    Returns the path to a saved standalone HTML map."""
    located = [f for f in features if f.get("lat") is not None and f.get("lon") is not None]

    if center:
        lat, lon = center
    elif located:
        lat = sum(f["lat"] for f in located) / len(located)
        lon = sum(f["lon"] for f in located) / len(located)
    else:
        lat, lon = 27.5, -81.5  # Florida-ish fallback

    # CARTO basemaps (Folium's "cartodbpositron") now need an API key and
    # render watermarked tiles without one; Esri's light-gray canvas is free.
    fmap = folium.Map(
        location=[lat, lon],
        zoom_start=9,
        tiles="https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        max_zoom=16,
    )

    for f in located:
        color = CATEGORY_COLOR.get(f["category"], DEFAULT_COLOR)
        folium.CircleMarker(
            location=[f["lat"], f["lon"]],
            radius=7,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=1,
            tooltip=f"{f['label']}" + (f" — {f['detail']}" if f.get("detail") else ""),
        ).add_to(fmap)

    legend_rows = "".join(
        f'<div><span style="background:{c};width:11px;height:11px;'
        f'border-radius:50%;display:inline-block;margin-right:5px;"></span>'
        f'{cat.replace("_", " ")}</div>'
        for cat, c in CATEGORY_COLOR.items()
        if any(f["category"] == cat for f in located)
    )
    if legend_rows:
        fmap.get_root().html.add_child(
            folium.Element(
                f'<div style="position:fixed;bottom:20px;left:20px;z-index:1000;'
                f'background:white;padding:8px 12px;border-radius:6px;font-size:12px;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.3);">{legend_rows}</div>'
            )
        )

    settings.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = settings.output_dir / f"hazard_map_{int(time.time())}_{uuid.uuid4().hex[:8]}.html"
    fmap.save(str(out_path))
    return str(out_path)
