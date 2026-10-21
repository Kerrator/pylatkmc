"""Path resolution for pylatkmc.ingest integration tests.

A handful of ingest tests read a live curated catalogue produced by
PyKMC_Analysis (https://github.com/Kerrator/PyKMC_Analysis): its
``rate_lookup_table_family.csv`` and the per-user ``audit_log.csv``. Those are
git-ignored outputs of that repo, not part of pylatkmc, so we resolve the
directory holding them here. Resolution order:

1. ``PYKMC_ANALYSIS_OUTPUT_DIR`` env var: the outputs directory itself (the same
   variable PyKMC_Analysis writes to).
2. ``PYKMC_KMC_ROOT`` env var (legacy): a workspace containing
   ``apps/PyKMC_Analysis/``; outputs are read from its default location.
3. Auto-detect: walk up from this file to a workspace with that sibling layout.

Tests that need a file call :func:`require_output`, which skips them when the
file is absent (no checkout, or a fresh clone with no outputs yet). The
pure-logic family/assignment/rate-table tests do not need any of it.

Separately, the event-representation pipeline tests (contract §§11.6-11.7) read a
real pyKMC **reference-table pickle**, resolved via :func:`reftable_path` /
:func:`require_reftable` below (``PYKMC_REFTABLE`` env var, else the two known
on-box pickles), skipping cleanly when none is present.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_DEFAULT_SUBDIR = Path("apps", "PyKMC_Analysis", "Analysis", "lattice_event_classification")


def _output_dir() -> tuple[Path | None, str]:
    """Return (directory, how it was found) for the classification outputs."""
    env = os.environ.get("PYKMC_ANALYSIS_OUTPUT_DIR")
    if env:
        return Path(env).expanduser().resolve(), "PYKMC_ANALYSIS_OUTPUT_DIR"
    env = os.environ.get("PYKMC_KMC_ROOT")
    if env:
        return Path(env).expanduser().resolve() / _DEFAULT_SUBDIR, "PYKMC_KMC_ROOT"
    for parent in Path(__file__).resolve().parents:
        if (parent / _DEFAULT_SUBDIR).is_dir():
            return parent / _DEFAULT_SUBDIR, "auto-detected sibling checkout"
    return None, "not found"


OUTPUT_DIR, _OUTPUT_DIR_SOURCE = _output_dir()


def require_output(name: str) -> Path:
    """Return ``OUTPUT_DIR / name``, or skip the calling test if it is absent."""
    if OUTPUT_DIR is None:
        pytest.skip(
            f"PyKMC_Analysis outputs not found ({name}); set PYKMC_ANALYSIS_OUTPUT_DIR "
            "to the directory holding them to run this test."
        )
    path = OUTPUT_DIR / name
    if not path.is_file():
        pytest.skip(f"{name} not found in {OUTPUT_DIR} (from {_OUTPUT_DIR_SOURCE}).")
    return path


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
