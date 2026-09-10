from __future__ import annotations

import sys
from pathlib import Path


EXTENDED_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]

sys.path.insert(0, str(REPO_ROOT / "python" / "src"))
sys.path.insert(0, str(EXTENDED_DIR))
