"""Test configuration for the MCP impact-analysis cookbook."""

from __future__ import annotations

import sys
from pathlib import Path


COOKBOOK_DIR = Path(__file__).resolve().parents[1]
if str(COOKBOOK_DIR) not in sys.path:
    sys.path.insert(0, str(COOKBOOK_DIR))
