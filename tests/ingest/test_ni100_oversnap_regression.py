"""Pure-Ni over-snapping policy regression (memo 2026-07-29 §4-§6, §8).

Pins the mover-keyed G3 discard + §6 bystander mask + CANON-v2 identity to the
simplest chemistry the engine must not regress on: the pure-Ni ``100Ni/10vac/
T500/full`` corpus (2,129 rows, Ni(100) slab, run rcut 8.5 Å, FULL coloring).
``ni_example`` only covers the family-CSV path; this suite covers the
EventClass/ingest path on pure Ni. Measured 2026-07-29 on that corpus:

* **Ledger partition** (§5 conservation): 2,129 = 1,891 kept + 238 discarded
  (all ``MOVER_OFFLATTICE``) + 0 raised; every kept row G3-PASS.
* **Identity**: the 1,891 kept rows form 1,731 classes (measured identical at
  CANON v2 and CANON v3 — the 2026-07-31 fingerprint bump relabelled every id
  but split nothing on this corpus; fixture regenerated then).
* **Masking** (§6): 1,133 kept rows carry >=1 WILDCARD-masked context row
  (59.9% -- far above the NiCr ~15-20% band; corpus property, the 10-vacancy
  slab relaxes more) with per-row counts pinned in the fixture.
* **No clean valley on this corpus**: kept mover residuals reach 0.499 Å and
  discards start at 0.501 Å (54 discards within 0.1 Å of the 0.5 Å threshold)
  -- unlike the NiCr demo corpus where the bimodal valley was empty. The
  threshold band is therefore sampled densely below.
* **Determinism**: two subprocess runs under different ``PYTHONHASHSEED``
  agree on (G3 outcome, discard reason, ``class_id``).

Expected values live in ``data/ni100_oversnap_expected.csv`` (regenerate with
the gen script recorded in the migration campaign notes). The suite skips
unless the resolved reference table matches the fixture (row count + ``idx_ref``
spot-check); override the corpus path with ``PYKMC_NI100_REFTABLE``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("pandas")
event_projection = pytest.importorskip("pylatkmc.ingest.event_projection")

import pandas as pd  # noqa: E402

from pylatkmc.ingest import canonical  # noqa: E402
from pylatkmc.ingest import event_class as ec  # noqa: E402
from pylatkmc.ingest.event_class import Coloring  # noqa: E402
from pylatkmc.ingest.reftable import _discard_reason  # noqa: E402

_FIXTURE = Path(__file__).parent / "data" / "ni100_oversnap_expected.csv"

#: The corpus the fixture was measured on (docstring Conditions block).
_NI100_REFTABLE = Path(
    "/home/kerr/pykmc/Clusters/Research/100Ni/10vac/T500/full/reference_table.pickle"
)
_RCUT = 8.5
_D_MAX = 3
_R_CTX_MIN = 3.6
_MOVER_SNAP_TOL = 0.5

# Locked aggregates (2026-07-29 measurement).
_N_ROWS = 2129
_N_KEPT = 1891
_N_DISCARDED = 238
_N_CLASSES = 1731
_N_MASKED_ROWS = 1133

_G3_NAMES = {0: "PASS", 1: "FAIL", 2: "WARN", 3: "NA"}


def _load_corpus() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve (reference table, fixture); skip unless they describe each other."""
    fixture = pd.read_csv(_FIXTURE, keep_default_na=False)
    env = os.environ.get("PYKMC_NI100_REFTABLE")
    path = Path(env).expanduser() if env else _NI100_REFTABLE
    if not path.is_file():
        pytest.skip(
            f"pure-Ni corpus not found ({path}); set PYKMC_NI100_REFTABLE to the "
            "100Ni/10vac/T500/full reference_table.pickle"
        )
    df = pd.read_pickle(path)
    if len(df) != len(fixture) or any(
        int(df.iloc[i]["idx_ref"]) != int(fixture["idx_ref"].iloc[i])
        for i in range(0, len(fixture), 50)
    ):
        pytest.skip(
            f"{path} is not the corpus the ni100 fixture was measured on "
            "(row count / idx_ref sequence mismatch)"
        )
    return df, fixture


@pytest.fixture(scope="module")
def corpus() -> tuple[pd.DataFrame, pd.DataFrame]:
    return _load_corpus()


def _project(df: pd.DataFrame, row: int) -> object:
    return event_projection.project_event(
        df.iloc[row],
        coloring=Coloring.FULL,
        rcut=_RCUT,
        d_max=_D_MAX,
        r_ctx_min=_R_CTX_MIN,
    )


def _sample_rows(fixture: pd.DataFrame) -> list[int]:
    """Deterministic projection sample: strides + the dense 0.4-0.6 Å band.

    Full re-projection of all 2,129 rows costs minutes; the sample keeps every
    stride-40 kept row, every stride-10 discard, and every 5th row of the
    threshold band where policy drift would surface first.
    """
    kept = fixture[fixture["discard_reason"] == ""]
    disc = fixture[fixture["discard_reason"] != ""]
    res = fixture["mover_max_residual"].astype(float)
    band = fixture[(res >= 0.4) & (res < 0.6)]
    rows = sorted(
        set(kept["row"].iloc[::40]) | set(disc["row"].iloc[::10]) | set(band["row"].iloc[::5])
    )
    return [int(r) for r in rows]


def test_fixture_aggregates() -> None:
    """The fixture file itself carries the locked partition/identity counts."""
    fx = pd.read_csv(_FIXTURE, keep_default_na=False)
    kept = fx[fx["discard_reason"] == ""]
    disc = fx[fx["discard_reason"] != ""]
    assert len(fx) == _N_ROWS
    assert len(kept) == _N_KEPT
    assert len(disc) == _N_DISCARDED
    assert (fx["g3"] != "RAISED").all(), "corpus projected without raises"
    assert set(disc["discard_reason"]) == {"MOVER_OFFLATTICE"}
    assert (kept["g3"] == "PASS").all()
    assert kept["class_id"].nunique() == _N_CLASSES
    assert (kept["class_id"] != "").all()
    assert int((kept["n_masked_ctx"].astype(int) > 0).sum()) == _N_MASKED_ROWS
    # §5 conservation: kept + discarded (+ 0 raised) is exact.
    assert len(kept) + len(disc) == _N_ROWS


def test_policy_partition_regression(corpus: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """Sampled rows re-project to the pinned (G3, reason, class_id, mask count)."""
    df, fixture = corpus
    by_row = fixture.set_index("row")
    for row in _sample_rows(fixture):
        pe = _project(df, row)
        exp = by_row.loc[row]
        dropped = _discard_reason(pe, _MOVER_SNAP_TOL)
        reason = dropped[0] if dropped else ""
        assert reason == exp["discard_reason"], f"row {row}: discard drifted"
        g3 = _G3_NAMES[int(ec.gate_g3_snap_residual(pe, _MOVER_SNAP_TOL).outcome)]
        assert g3 == exp["g3"], f"row {row}: G3 outcome drifted"
        n_masked = sum(1 for cs in pe.context if cs.pred.kind == "WILDCARD")
        assert n_masked == int(exp["n_masked_ctx"]), f"row {row}: mask count drifted"
        if not dropped:
            assert canonical.class_id(pe) == exp["class_id"], (
                f"row {row}: class_id drifted from the locked CANON-v2 id"
            )


def test_threshold_band_is_pinned(corpus: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """The 0.5 Å cut through this corpus's residual continuum stays put.

    Kept residuals reach 0.499 Å; discards start at 0.501 Å. A tolerance or
    residual-computation drift flips band rows first.
    """
    df, fixture = corpus
    res = fixture["mover_max_residual"].astype(float)
    kept_band = fixture[(fixture["discard_reason"] == "") & (res >= 0.45)]
    disc_band = fixture[(fixture["discard_reason"] != "") & (res < 0.55)]
    assert len(kept_band) == 106
    assert len(disc_band) == 34
    for row in [int(r) for r in kept_band["row"].iloc[::20]]:
        assert _discard_reason(_project(df, row), _MOVER_SNAP_TOL) is None
    for row in [int(r) for r in disc_band["row"].iloc[::20]]:
        dropped = _discard_reason(_project(df, row), _MOVER_SNAP_TOL)
        assert dropped is not None and dropped[0] == "MOVER_OFFLATTICE"


_DETERMINISM_SCRIPT = """
import sys
import pandas as pd
from pylatkmc.ingest import canonical
from pylatkmc.ingest.event_projection import project_event
from pylatkmc.ingest.event_class import Coloring
from pylatkmc.ingest.reftable import _discard_reason

df = pd.read_pickle(sys.argv[1])
for row in [int(r) for r in sys.argv[2].split(",")]:
    pe = project_event(df.iloc[row], coloring=Coloring.FULL, rcut=8.5, d_max=3,
                       r_ctx_min=3.6)
    dropped = _discard_reason(pe, 0.5)
    if dropped:
        print(row, "DISCARDED", dropped[0])
    else:
        print(row, "KEPT", canonical.class_id(pe))
"""


def test_partition_deterministic_across_hashseed(
    corpus: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Two PYTHONHASHSEED runs agree on (kept/discarded, reason, class_id)."""
    df, fixture = corpus
    del df
    kept = fixture[fixture["discard_reason"] == ""]
    disc = fixture[fixture["discard_reason"] != ""]
    rows = sorted(
        {int(r) for r in kept["row"].iloc[::100]} | {int(r) for r in disc["row"].iloc[::25]}
    )
    rows_arg = ",".join(str(r) for r in rows)
    env = os.environ.get("PYKMC_NI100_REFTABLE")
    path = str(Path(env).expanduser() if env else _NI100_REFTABLE)

    outputs = []
    for seed in ("0", "1"):
        run_env = dict(os.environ, PYTHONHASHSEED=seed)
        proc = subprocess.run(
            [sys.executable, "-c", _DETERMINISM_SCRIPT, path, rows_arg],
            capture_output=True,
            text=True,
            env=run_env,
            check=True,
        )
        outputs.append(proc.stdout)
    assert outputs[0] == outputs[1], "partition/class_ids differ across PYTHONHASHSEED"

    by_row = fixture.set_index("row")
    for line in outputs[0].strip().splitlines():
        row_s, status, detail = line.split()
        exp = by_row.loc[int(row_s)]
        if status == "DISCARDED":
            assert exp["discard_reason"] == detail, f"row {row_s} drifted from fixture"
        else:
            assert exp["class_id"] == detail, f"row {row_s} drifted from fixture"
