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

Separately, the event-representation pipeline tests (contract §§11.6-11.7) read a
real pyKMC **reference-table pickle**, resolved via :func:`reftable_path` /
:func:`require_reftable` below (``PYKMC_REFTABLE`` env var, else the two known
on-box pickles), skipping cleanly when none is present.
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


# --- pyKMC reference-table resolution (contract §§11.6-11.7) ---------------

#: Environment variable naming a pyKMC ``reference_table.pickle`` to test against.
REFTABLE_ENV = "PYKMC_REFTABLE"

#: Known on-box reference-table pickles, tried in order when ``PYKMC_REFTABLE``
#: is unset (contract §11.6). Missing entries are skipped, never fatal.
DEFAULT_REFTABLES: tuple[Path, ...] = (
    Path("/home/kerr/pykmc/scratch_nicr_htst/reference_table.pickle"),
    Path("/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle"),
)


def reftable_path() -> Path | None:
    """Resolve a pyKMC reference-table pickle for the ingest pipeline tests.

    Resolution order (contract §11.6): the ``PYKMC_REFTABLE`` env var if set,
    then the two known on-box pickles in :data:`DEFAULT_REFTABLES`. Returns the
    first existing file, or ``None`` when none is present so the caller can skip
    (never fail).
    """
    candidates: list[Path] = []
    env = os.environ.get(REFTABLE_ENV)
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend(DEFAULT_REFTABLES)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def require_reftable() -> Path:
    """Return a resolvable reference-table pickle or skip the calling test.

    Skips (never fails) when neither ``PYKMC_REFTABLE`` nor a known on-box pickle
    is present (contract §11.6).
    """
    path = reftable_path()
    if path is None:
        pytest.skip(
            "no pyKMC reference table found; set PYKMC_REFTABLE to a "
            "reference_table.pickle to run the ingest pipeline tests."
        )
    return path
