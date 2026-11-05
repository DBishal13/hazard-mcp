import os
import time

import pytest

from hazard_mcp import cache
from hazard_mcp.config import settings


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "cache_dir", tmp_path)
    monkeypatch.setattr(settings, "cache_enabled", True)
    monkeypatch.setitem(cache.TTL, "test", 60)
    return tmp_path


def make_counter():
    calls = []

    @cache.cached("test")
    def fetch(bbox, days=1):
        calls.append((bbox, days))
        return [{"n": len(calls)}]

    return fetch, calls


def test_second_call_is_served_from_disk():
    fetch, calls = make_counter()
    assert fetch((1.0, 2.0, 3.0, 4.0)) == [{"n": 1}]
    assert fetch((1.0, 2.0, 3.0, 4.0)) == [{"n": 1}]
    assert len(calls) == 1


def test_near_identical_floats_share_an_entry_and_kwargs_match_positional():
    fetch, calls = make_counter()
    fetch((1.0, 2.0, 3.0, 4.0), 1)
    fetch(bbox=(1.00000001, 2.0, 3.0, 4.0), days=1)
    fetch((1.0, 2.0, 3.0, 4.0))  # default filled in -> same key
    assert len(calls) == 1


def test_different_args_miss():
    fetch, calls = make_counter()
    fetch((1.0, 2.0, 3.0, 4.0), days=1)
    fetch((1.0, 2.0, 3.0, 4.0), days=2)
    assert len(calls) == 2


def test_expired_entry_refetches(tmp_cache):
    fetch, calls = make_counter()
    fetch((1.0, 2.0, 3.0, 4.0))
    old = time.time() - 120
    for f in (tmp_cache / "test").iterdir():
        os.utime(f, (old, old))
    fetch((1.0, 2.0, 3.0, 4.0))
    assert len(calls) == 2


def test_exceptions_are_not_cached():
    attempts = []

    @cache.cached("test")
    def flaky(x):
        attempts.append(x)
        if len(attempts) == 1:
            raise RuntimeError("upstream 503")
        return {"ok": True}

    with pytest.raises(RuntimeError):
        flaky(1)
    assert flaky(1) == {"ok": True}
    assert len(attempts) == 2


def test_corrupt_file_is_a_miss(tmp_cache):
    fetch, _ = make_counter()
    fetch((1.0, 2.0, 3.0, 4.0))
    for f in (tmp_cache / "test").iterdir():
        f.write_text("{not json")
    assert fetch((1.0, 2.0, 3.0, 4.0)) == [{"n": 2}]


def test_disabled_always_calls_through(monkeypatch):
    monkeypatch.setattr(settings, "cache_enabled", False)
    fetch, calls = make_counter()
    fetch((1.0, 2.0, 3.0, 4.0))
    fetch((1.0, 2.0, 3.0, 4.0))
    assert len(calls) == 2


def test_unwritable_cache_does_not_break_the_call(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    monkeypatch.setattr(settings, "cache_dir", blocker)
    fetch, _ = make_counter()
    assert fetch((1.0, 2.0, 3.0, 4.0)) == [{"n": 1}]


def test_every_real_client_is_wrapped():
    from hazard_mcp.data import (
        geocode,
        nasa_eonet,
        nasa_firms,
        nwps,
        nws_alerts,
        openfema,
        usgs_earthquakes,
    )

    for fn in [
        geocode._geocode_place, openfema.disaster_declarations, openfema.nfip_claims,
        nws_alerts.active_alerts_near, nws_alerts.active_alerts_in_state,
        usgs_earthquakes.earthquakes, nasa_eonet.events, nasa_firms.active_fires,
        nwps.gauges_in_bbox, nwps.gauge_stageflow, nwps.flood_inundation_extent,
    ]:
        assert hasattr(fn, "uncached"), fn.__qualname__
