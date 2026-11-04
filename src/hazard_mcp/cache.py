"""Disk-backed TTL cache for upstream hazard API responses.

location_risk_summary fans out to seven sources on every call, and agents
tend to ask about the same place several times in one conversation (summary,
then a map, then a follow-up). Caching each source's response on disk makes
those repeat calls near-instant and keeps us polite to free public APIs.

Same pattern as surge-exposure's api/cache.py: JSON files under
data/cache/<namespace>/, keyed by a hash of the call arguments, expired by
file mtime. Disk rather than an in-memory dict so the cache survives a
container restart.

Each source gets its own TTL because the data changes at very different
rates -- NWS alerts can change minute to minute, FEMA declarations are
effectively daily, and a geocode result essentially never changes.

Only successful return values are cached: if the wrapped function raises,
nothing is written, so a transient upstream failure isn't pinned for the
whole TTL.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
import os
import tempfile
import time
from collections.abc import Callable
from typing import Any, TypeVar

from hazard_mcp.config import settings

F = TypeVar("F", bound=Callable[..., Any])

# TTLs in seconds, per source. Tuned for "demo / agent assistant", not an
# operational warning system -- anything life-safety should hit the source.
TTL = {
    "geocode": 30 * 24 * 3600,  # place -> lat/lon is effectively static
    "openfema_declarations": 6 * 3600,
    "openfema_nfip": 24 * 3600,  # NFIP redacted claims refresh ~monthly
    "nws_alerts": 5 * 60,  # alerts are issued/cancelled continuously
    "usgs_earthquakes": 15 * 60,
    "nasa_eonet": 60 * 60,
    "nasa_firms": 30 * 60,  # NRT detections land a few times an hour
    "nwps_gauges": 6 * 3600,  # gauge metadata, not readings
    "nwps_stageflow": 15 * 60,
    "nwm_fim": 30 * 60,  # NWM analysis inundation updates hourly
}


def _normalize(value: Any) -> Any:
    """Make args JSON-stable: round floats so near-identical bboxes hit the
    same entry, and turn tuples into lists."""
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in sorted(value.items())}
    return value


def make_key(namespace: str, bound_args: dict[str, Any]) -> str:
    raw = json.dumps([namespace, _normalize(bound_args)], sort_keys=True, default=str)
    return hashlib.sha1(raw.encode()).hexdigest()


def _path(namespace: str, key: str):
    return settings.cache_dir / namespace / f"{key}.json"


def get(namespace: str, key: str, ttl: float) -> tuple[bool, Any]:
    path = _path(namespace, key)
    try:
        if (time.time() - path.stat().st_mtime) > ttl:
            return False, None
        return True, json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # Missing, unreadable, or half-written (e.g. a crash mid-write
        # before atomic writes existed) -- treat as a miss.
        return False, None


def put(namespace: str, key: str, value: Any) -> None:
    path = _path(namespace, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-rename so a concurrent reader never sees a partial file.
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(value, f)
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        # A cache write failing (read-only FS, unserializable value) must
        # never break the actual tool call.
        try:
            os.unlink(tmp)  # type: ignore[possibly-undefined]
        except (OSError, NameError):
            pass


def cached(namespace: str) -> Callable[[F], F]:
    """Decorate a data-client function to cache its return value on disk
    for TTL[namespace] seconds. Disabled when settings.cache_enabled is
    False (HAZARD_MCP_CACHE_ENABLED=false)."""
    ttl = TTL[namespace]

    def decorator(func: F) -> F:
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.cache_enabled:
                return func(*args, **kwargs)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            key = make_key(namespace, dict(bound.arguments))
            hit, value = get(namespace, key, ttl)
            if hit:
                return value
            value = func(*args, **kwargs)
            put(namespace, key, value)
            return value

        wrapper.uncached = func  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
