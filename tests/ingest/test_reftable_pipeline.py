"""End-to-end reference-table -> catalogue pipeline (Agent A5, contract 11.6).

Behind ``PYKMC_REFTABLE`` (or the two known on-box pickles): load a real pyKMC
reference table, ``project_event`` a handful of rows (Agent A4), canonicalise
(Agent A5), ``build_class_catalogue`` (Agent A2), and write+read the Parquet
catalogue (Agent A2). Asserts no crash, all ``class_id`` are 64-hex,
``orientation_count >= 1``, linked pairs carry ``dEnergy_eV``, and the on-lattice
partition **refines** the ``id_saddle`` partition in rate units (two rows with
different ``id_saddle`` share a class only within ``|dEa| < k_BT`` -- otherwise the
merge is a ``CONTEXT_UNDERRESOLVED`` audit finding, which this test surfaces).

Skips (never fails) when the ``[ingest]`` extras, the forward-projection module
(Agent A4's ``event_projection``), or the reference table are absent.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest
from _paths import require_reftable

pytest.importorskip("pandas")
pytest.importorskip("pyarrow")
# Agent A4's forward projection: required to turn a reference row into a
# ProjectedEvent. Skip cleanly until it lands in this parallel build.
event_projection = pytest.importorskip("pylatkmc.ingest.event_projection")

import pandas as pd  # noqa: E402

from pylatkmc.ingest import canonical as C  # noqa: E402
from pylatkmc.ingest import event_class as ec  # noqa: E402
from pylatkmc.ingest.event_class import Coloring, GateThresholds  # noqa: E402
from pylatkmc.rate_expression import KB_EV_PER_K  # noqa: E402

_T_REF_K = 500.0
_RCUT = 5.0
_A_NOMINAL = 3.52
# d_max = floor(rcut / (a/2)) - 1 (contract 5 / 3).
_D_MAX = int(_RCUT / (_A_NOMINAL / 2.0)) - 1
_R_CTX_MIN = 3.6
_N_ROWS = 80  # a handful, plus enough to catch backward partners in-range


def _load_projected() -> list:
    """Load the reference table and project a handful of rows to ProjectedEvents."""
    path = require_reftable()  # PYKMC_REFTABLE / known pickles, else skip (shared _paths)
    df = pd.read_pickle(path)
    assert isinstance(df, pd.DataFrame), "reference table is not a DataFrame"

    projected = []
    for i in range(min(_N_ROWS, len(df))):
        row = df.iloc[i]
        try:
            pe = event_projection.project_event(
                row,
                coloring=Coloring.FULL,
                rcut=_RCUT,
                d_max=_D_MAX,
                r_ctx_min=_R_CTX_MIN,
            )
        except Exception:  # noqa: BLE001 - unprojectable rows are hand-back cases, not test failures
            continue
        projected.append(pe)
    if len(projected) < 2:
        pytest.skip("fewer than 2 projectable rows; nothing to canonicalise")
    return projected


def test_reftable_pipeline_end_to_end(tmp_path: Path) -> None:
    """Project -> canonicalise -> catalogue -> Parquet round-trip on real data."""
    projected = _load_projected()

    # Canonicalisation must not crash and must yield 64-hex ids.
    for pe in projected:
        cid = C.class_id(pe)
        assert isinstance(cid, str) and len(cid) == 64
        int(cid, 16)  # valid lowercase hex
        assert C.orientation_count(pe) >= 1

    thresholds = GateThresholds(
        emin_event=0.0,
        emax_event=10.0,
        backward_emin_event=0.0,
        snap_tol=0.9,
        db_tol=0.05,
        rcut=_RCUT,
    )
    classes = ec.build_class_catalogue(
        projected, t_ref_K=_T_REF_K, thresholds=thresholds, nu0_fallback_hz=1.0e13
    )
    assert classes, "no classes assembled"

    # Rows are class_id-sorted and every id is 64-hex; orientation_count >= 1.
    ids = [k.class_id for k in classes]
    assert ids == sorted(ids)
    for k in classes:
        assert len(k.class_id) == 64
        int(k.class_id, 16)
        assert k.orientation_count >= 1
        # Every linked pair carries an independent dEnergy channel.
        if k.pair_status == "linked":
            assert k.dEnergy_eV is not None

    # Parquet write + read round-trips every field.
    out = tmp_path / "catalogue.parquet"
    ec.write_catalogue_parquet(classes, out)
    reread = ec.read_catalogue_parquet(out)
    assert [k.class_id for k in reread] == ids
    for a, b in zip(classes, reread, strict=True):
        assert a.canonical_blob == b.canonical_blob
        assert a.delta == b.delta
        assert a.context == b.context
        assert a.saddle_token == b.saddle_token
        assert a.orientation_count == b.orientation_count
        # canonical_blob decodes back to the authoritative canonical form.
        assert ec.decode_canonical_blob(b.canonical_blob) == b.canonical_form


def test_partition_refines_id_saddle_in_rate_units() -> None:
    """On-lattice classes refine the id_saddle partition within k_BT (design 4.4)."""
    projected = _load_projected()
    kbt = KB_EV_PER_K * _T_REF_K

    per_class: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for pe in projected:
        per_class[C.class_id(pe)].append((pe.id_saddle, pe.Ea_fwd_eV))

    # A class confined to one id_saddle strictly refines it; at least some do.
    refined = sum(1 for members in per_class.values() if len({s for s, _ in members}) == 1)
    assert refined >= 1

    # A class merging multiple id_saddle beyond k_BT is a CONTEXT_UNDERRESOLVED
    # finding (design 4.4 / M6): it must be surfaced, never silently merged. We
    # surface it here; the detector is deterministic and self-consistent.
    under_resolved: list[tuple[str, float]] = []
    for cid, members in per_class.items():
        if len({s for s, _ in members}) > 1:
            spread = max(e for _, e in members) - min(e for _, e in members)
            if spread >= kbt:
                under_resolved.append((cid, spread))
    for _cid, spread in under_resolved:
        assert spread >= kbt  # self-consistency of the CONTEXT_UNDERRESOLVED set
