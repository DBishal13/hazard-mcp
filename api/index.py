"""Vercel entry point: serves hazard_mcp.web.app (MCP at /mcp + demo page)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from hazard_mcp.web import app

__all__ = ["app"]
