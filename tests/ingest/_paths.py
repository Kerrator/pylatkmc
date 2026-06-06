"""Path resolution for pylatkmc.ingest integration tests.

A handful of ingest tests read the live curated catalogue produced by the
apps/PyKMC_Analysis pipeline (audit_log.csv, rate_lookup_table_family.csv).
That data lives in the shared `kmc/` workspace, not in the pylatkmc repo, so we
resolve it here rather than hardcoding. Resolution order:

1. ``PYKMC_KMC_ROOT`` env var (a tree containing ``apps/PyKMC_Analysis/``).
2. Auto-detect: walk up from this file to the workspace root that has an
   ``apps/PyKMC_Analysis/`` sibling.

If the data can't be found, ``CLASSIFICATION_DIR`` points at a non-existent path
and the data-dependent tests should skip (see ``_require_classification_data``).
The pure-logic family/assignment/rate-table tests do not need it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _kmc_root() -> Path | None:
    env = os.environ.get("PYKMC_KMC_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        return p if (p / "apps" / "PyKMC_Analysis").is_dir() else None
    for parent in Path(__file__).resolve().parents:
        if (parent / "apps" / "PyKMC_Analysis").is_dir():
            return parent
    return None


_ROOT = _kmc_root()
CLASSIFICATION_DIR: Path = (
    _ROOT / "apps" / "PyKMC_Analysis" / "Analysis" / "lattice_event_classification"
    if _ROOT is not None
    else Path("/__pylatkmc_no_classification_data__")
)
AUDIT_CSV: Path = CLASSIFICATION_DIR / "audit_log.csv"


def require_classification_data() -> None:
    """Skip the calling test when the apps/ curated catalogue isn't present."""
    if not CLASSIFICATION_DIR.is_dir():
        pytest.skip(
            "apps/PyKMC_Analysis curated catalogue not found; set PYKMC_KMC_ROOT "
            "to the kmc workspace to run ingest integration tests."
        )
