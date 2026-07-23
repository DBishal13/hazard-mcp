from hazard_mcp.data.geocode import bbox_around


def test_bbox_around_is_centered_and_symmetric():
    lat, lon, radius_km = 26.14, -81.79, 50
    min_lon, min_lat, max_lon, max_lat = bbox_around(lat, lon, radius_km)

    assert min_lon < lon < max_lon
    assert min_lat < lat < max_lat
    # Symmetric around the center point.
    assert abs((lon - min_lon) - (max_lon - lon)) < 1e-9
    assert abs((lat - min_lat) - (max_lat - lat)) < 1e-9


def test_bbox_around_shrinks_longitude_span_at_higher_latitude():
    _, _, max_lon_low, _ = bbox_around(10.0, 0.0, 100)
    _, _, max_lon_high, _ = bbox_around(60.0, 0.0, 100)
    # Same radius_km spans more degrees of longitude closer to the poles.
    assert (max_lon_high - 0.0) > (max_lon_low - 0.0)
