"""Pytest configuration for pylatkmc/pylatkmc unit tests.

Adds the repo root to sys.path so `from pylatkmc import ...` resolves
without needing an editable install. The package stays installable via
`pip install -e .` for users who prefer that.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
