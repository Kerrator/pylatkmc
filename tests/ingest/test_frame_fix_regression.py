"""Frame-fix regression suite (identity-redesign memo 2026-07-22, §6 criteria).

Locks the robust global-orientation frame fit + pinned identity scale to the
numbers the prototype validated on the production NiCr ``verify_fix_T500_1vac``
corpus, re-measured through the INSTALLED pipeline:

* **PASS bijection** (§6.2): the 124 previously-G3-PASS events stay PASS and their
  123 old classes map 1:1 onto 123 new classes — zero splits, zero joins.
* **Bucket-(ii) recovery** (§6.1): all 41 triage-bucket-(ii) events project
  G3-PASS, single-mover, atom-conserving.
* **Determinism**: two subprocess runs under different ``PYTHONHASHSEED`` produce
  identical ``class_id``\\ s (contract Phase A hard gate).

The expected values live in ``data/frame_fix_expected.csv``. First written from
the 2026-07-22 validation (where the installed pipeline reproduced the prototype
445/445, with 63 ids bit-identical to the pre-fix era); **regenerated 2026-07-29**
under the over-snapping policy (mover-keyed G3 @ 0.5 Å, §6 bystander mask,
``CANON_SCHEMA_VERSION`` 2): the PASS bijection and bucket-(ii) recovery are
unchanged, and the CANON version prefix relabels every id (bit-identical count is
0 by construction). The suite is pinned to that corpus: it skips unless the
resolved reference table's positional ``idx_ref`` sequence matches the fixture.
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

_FIXTURE = Path(__file__).parent / "data" / "frame_fix_expected.csv"

#: The corpus the fixture was measured on (memo Conditions block).
_PRODUCTION_REFTABLE = Path(
    "/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle"
)
_RCUT = 8.5
_D_MAX = 3
_R_CTX_MIN = 3.6
_MOVER_SNAP_TOL = 0.5  # memo 2026-07-29 §4 (the retired max-keyed gate used 0.9)


def _load_corpus() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve (reference table, fixture); skip unless they describe each other."""
    fixture = pd.read_csv(_FIXTURE)
    env = os.environ.get("PYKMC_REFTABLE")
    path = Path(env).expanduser() if env else _PRODUCTION_REFTABLE
    if not path.is_file():
        pytest.skip(
            f"frame-fix corpus not found ({path}); set PYKMC_REFTABLE to the "
            "production verify_fix_T500_1vac reference_table.pickle"
        )
    df = pd.read_pickle(path)
    if len(df) != len(fixture) or any(
        int(df.iloc[i]["idx_ref"]) != int(fixture["idx_ref"].iloc[i])
        for i in range(0, len(fixture), 50)
    ):
        pytest.skip(
            f"{path} is not the corpus the frame-fix fixture was measured on "
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


def _g3(pe: object) -> str:
    res = ec.gate_g3_snap_residual(pe, _MOVER_SNAP_TOL)
    return {0: "PASS", 1: "FAIL", 2: "WARN", 3: "NA"}[int(res.outcome)]


def test_pass_bijection_regression(corpus: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """§6.2: old-PASS events keep PASS; classes map 1:1 (0 splits / 0 joins)."""
    df, fixture = corpus
    p = fixture[fixture["g3_old"] == "PASS"].copy()
    assert len(p) == 124

    impl_ids: list[str] = []
    n_pass = 0
    for row in p["row"]:
        pe = _project(df, int(row))
        impl_ids.append(canonical.class_id(pe))
        n_pass += _g3(pe) == "PASS"
    p["impl_id"] = impl_ids

    assert n_pass == 124, f"only {n_pass}/124 old-PASS events still G3-PASS"
    mismatch = int((p["impl_id"] != p["class_id_new"]).sum())
    assert mismatch == 0, f"{mismatch} events drifted from the locked class_id_new"

    fwd = p.groupby("class_id_old")["impl_id"].nunique()
    back = p.groupby("impl_id")["class_id_old"].nunique()
    assert p["class_id_old"].nunique() == 123
    assert p["impl_id"].nunique() == 123
    assert int((fwd > 1).sum()) == 0, "old class split under the new identity"
    assert int((back > 1).sum()) == 0, "old classes joined under the new identity"
    # CANON v2 (2026-07-29) prefixes every id: none stay bit-identical to the
    # pre-frame-fix era (was 63 under CANON v1).
    assert int((p["class_id_old"] == p["impl_id"]).sum()) == 0


def test_bucket_ii_recovery(corpus: tuple[pd.DataFrame, pd.DataFrame]) -> None:
    """§6.1: all 41 bucket-(ii) events are G3-PASS, single-mover, conserving."""
    df, fixture = corpus
    rows = fixture.loc[fixture["bucket"] == "ii", "row"]
    assert len(rows) == 41
    for row in rows:
        pe = _project(df, int(row))
        assert _g3(pe) == "PASS", f"bucket-(ii) row {row} not recovered"
        assert len(pe.movers) == 1, f"bucket-(ii) row {row} not single-mover"
        assert pe.delta_atoms == 0, f"bucket-(ii) row {row} not atom-conserving"
        assert (
            canonical.class_id(pe) == fixture.loc[fixture["row"] == row, "class_id_new"].iloc[0]
        ), f"bucket-(ii) row {row} drifted from the locked class_id_new"


_DETERMINISM_SCRIPT = """
import sys
import pandas as pd
from pylatkmc.ingest import canonical
from pylatkmc.ingest.event_projection import project_event
from pylatkmc.ingest.event_class import Coloring

df = pd.read_pickle(sys.argv[1])
for row in [int(r) for r in sys.argv[2].split(",")]:
    pe = project_event(df.iloc[row], coloring=Coloring.FULL, rcut=8.5, d_max=3,
                       r_ctx_min=3.6)
    print(row, canonical.class_id(pe))
"""


def test_class_ids_deterministic_across_hashseed(
    corpus: tuple[pd.DataFrame, pd.DataFrame],
) -> None:
    """Two PYTHONHASHSEED runs produce identical class_ids (Phase A hard gate)."""
    df, fixture = corpus
    del df
    rows = ",".join(str(int(r)) for r in fixture["row"].iloc[::40])
    env = os.environ.get("PYKMC_REFTABLE")
    path = str(Path(env).expanduser() if env else _PRODUCTION_REFTABLE)

    outputs = []
    for seed in ("0", "1"):
        run_env = dict(os.environ, PYTHONHASHSEED=seed)
        proc = subprocess.run(
            [sys.executable, "-c", _DETERMINISM_SCRIPT, path, rows],
            capture_output=True,
            text=True,
            env=run_env,
            check=True,
        )
        outputs.append(proc.stdout)
    assert outputs[0] == outputs[1], "class_ids differ across PYTHONHASHSEED"

    expected = {int(r): cid for r, cid in zip(fixture["row"], fixture["class_id_new"], strict=True)}
    for line in outputs[0].strip().splitlines():
        row_s, cid = line.split()
        assert expected[int(row_s)] == cid, f"row {row_s} drifted from fixture"
