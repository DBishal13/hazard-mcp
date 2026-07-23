from hazard_mcp.mapping import CATEGORY_COLOR, render_map


def test_render_map_writes_html_file(tmp_path, monkeypatch):
    from hazard_mcp import config

    monkeypatch.setattr(config.settings, "output_dir", tmp_path)

    features = [
        {"category": "earthquake", "lat": 34.0, "lon": -118.0, "label": "Test quake", "detail": "M4.5"},
        {"category": "wildfire", "lat": 34.1, "lon": -118.1, "label": "Test fire"},
        {"category": "unknown_type", "lat": 34.2, "lon": -118.2, "label": "Unrecognized category"},
    ]
    path = render_map(features)

    assert path.startswith(str(tmp_path))
    content = open(path).read()
    assert "Test quake" in content
    assert "Test fire" in content


def test_render_map_skips_features_without_coordinates(tmp_path, monkeypatch):
    from hazard_mcp import config

    monkeypatch.setattr(config.settings, "output_dir", tmp_path)

    features = [
        {"category": "earthquake", "lat": None, "lon": None, "label": "No coords"},
    ]
    # Should not raise even though every feature is unlocated.
    path = render_map(features)
    assert open(path).read()


def test_category_colors_are_distinct_hex():
    assert len(CATEGORY_COLOR) == len(set(CATEGORY_COLOR.values()))
    for color in CATEGORY_COLOR.values():
        assert color.startswith("#") and len(color) == 7
