"""Over-snapping policy tests (decision memo 2026-07-29, §11 test list).

Covers the §4–§6 + §8.1 implementation slice:

* **§11-i** — mover-keyed G3 regression: an event failing *only* on mover residual
  FAILs (would have caught the pre-2026-07-29 dead mover branch); bystander-only
  relaxation PASSes. (The gate-level half also lives in
  ``test_ingest_rate_agg.test_g3_snap_residual_fires``; here it runs through a real
  projection.)
* **§11-ii** — a snap-flicker phantom mover (site assignment flips with no real
  move) registers as a *mover* via ``detect_movers`` and is gated to the discard
  ledger, never masked (phantom-delta protection).
* **§11-iii** — §6 masking: a static bystander ≥ 0.5 Å demotes its context row to
  ``WILDCARD``; delta sites and ``EMPTY`` rows are never masked; movers are never
  masked; the mask feeds ``depth_sig`` and the canonical identity.
* **§11-iv** — ledger conservation through ``project_reference_table``:
  ``n_rows = n_projected + n_raised + n_discarded``, with ``FRAME_UNFIT`` rows
  relocated to the ledger (convention change vs memo 2026-07-22 §3.6).
* **§11-vi** — two-``PYTHONHASHSEED`` byte-determinism of the rebuilt catalogue
  parquet *and* its discard-ledger sidecar.
* **§11-vii** — ``ni_example``'s committed proclist is byte-identical under
  regeneration (the family-CSV path is untouched by the ingest policy change).

(§11-v, the stamp-remap round-trip, belongs to the migration slice — the remap
script does not exist yet.)
"""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from pylatkmc.ingest.event_class import (
    Coloring,
    GateOutcome,
    GateThresholds,
    run_gates,
)
from pylatkmc.ingest.event_projection import project_event
from pylatkmc.ingest.reftable import (
    ReftableBuildReport,
    discard_ledger_path,
    project_reference_table,
)

H = 1.76  # half spacing a/2 for a = 3.52 A
NN = H * math.sqrt(2.0)  # 1NN spacing ~ 2.489 A


# --------------------------------------------------------------------------- #
# Cluster builders (house style of test_ingest_event_projection)              #
# --------------------------------------------------------------------------- #
def _ball_sites(rad2: int) -> list[tuple[int, int, int]]:
    """Even-parity offsets within squared index radius ``rad2`` of the origin, sorted."""
    reach = int(math.isqrt(rad2)) + 1
    out = [
        (i, j, k)
        for i in range(-reach, reach + 1)
        for j in range(-reach, reach + 1)
        for k in range(-reach, reach + 1)
        if (i + j + k) % 2 == 0 and i * i + j * j + k * k <= rad2
    ]
    return sorted(out)


def _cart(off: tuple[int, int, int]) -> np.ndarray:
    """Ideal Cartesian position of an integer offset (R = I)."""
    return H * np.asarray(off, dtype=float)


def _positions(occ: dict[tuple[int, int, int], str]):
    """Return (positions, types, sorted_sites) for an occupancy dict, sorted by site."""
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    return pos, types, sites


def _row(**kw):
    """A reference-row mapping with sane defaults for the fields project_event reads."""
    base = dict(
        energy_barrier=0.6,
        k=1.0e6,
        k_prefactor=1.0e13,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        source_row=0,
        cell=None,
    )
    base.update(kw)
    return base


def _thresholds() -> GateThresholds:
    """Permissive barrier thresholds so structural properties drive outcomes."""
    return GateThresholds(emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0)


class _FakeDF:
    """Minimal DataFrame stand-in for ``project_reference_table`` (len + iloc)."""

    def __init__(self, rows):
        self.iloc = rows

    def __len__(self) -> int:
        return len(self.iloc)


def _hop_event(bystander_shift_A: float = 0.0, *, shift_site=(0, 2, 0), **project_kw):
    """A clean Ni hop into a vacancy, optionally with a displaced static bystander.

    The bystander at ``shift_site`` is displaced ``bystander_shift_A`` toward an
    occupied neighbour, identically in both snapshots (static: its snap never
    flips for shifts < NN/2 ~ 1.24 A). The mover/seed at the origin is exact, so
    the frame is exact and every residual is the planted displacement.
    """
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]  # vacancy target
    pos, types, sites = _positions(occ)
    mi = sites.index((0, 0, 0))
    bi = sites.index(shift_site)
    if bystander_shift_A:
        direction = (_cart((1, 3, 0)) - _cart(shift_site)) / NN  # toward an occupied 1NN
        pos = pos.copy()
        pos[bi] = pos[bi] + bystander_shift_A * direction
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))
    row = _row(
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
    )
    pe = project_event(row, coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0, **project_kw)
    return pe, row


def _flicker_row(idx_ref: int = 0):
    """A snap-flicker phantom mover: site assignment flips, no real move (§11-ii).

    Atom B sits between its home site and an adjacent vacancy: 1.15 A out in P0
    (still snaps home), 1.35 A out in P2 (snaps to the vacancy) — a 0.2 A physical
    wobble that flips the site assignment. B must register as a MOVER (gated),
    never as a maskable bystander.
    """
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]  # seed's vacancy target
    del occ[(1, -1, 2)]  # the flicker atom's adjacent empty site
    b_home = (0, 0, 2)
    pos, types, sites = _positions(occ)
    mi = sites.index((0, 0, 0))
    bi = sites.index(b_home)
    direction = (_cart((1, -1, 2)) - _cart(b_home)) / NN
    pos = pos.copy()
    pos[bi] = _cart(b_home) + 1.15 * direction
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))  # the seed's real hop
    P2[bi] = _cart(b_home) + 1.35 * direction  # B crosses the Voronoi boundary
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))
    return _row(
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
        idx_ref=idx_ref,
        source_row=idx_ref,
        event_id=f"flicker{idx_ref}",
    ), b_home


def _ctx_kind(pe, site) -> str:
    """The context predicate kind at ``site`` (must exist)."""
    for cs in pe.context:
        if cs.off == site:
            return cs.pred.kind
    raise AssertionError(f"site {site} not in context")


# --------------------------------------------------------------------------- #
# §11-i — mover-keyed G3 through a real projection                            #
# --------------------------------------------------------------------------- #
def test_bystander_relaxation_passes_g3() -> None:
    """A 0.95 A static bystander no longer FAILs G3 (movers are tight)."""
    pe, _ = _hop_event(bystander_shift_A=0.95)
    assert pe.proj_report.mover_max_residual < 1e-9
    assert pe.proj_report.max_residual == pytest.approx(0.95, abs=0.02)
    g3 = next(g for g in run_gates(pe, thresholds=_thresholds()) if g.gate == "G3")
    assert g3.outcome == GateOutcome.PASS


def test_mover_offlattice_fails_g3() -> None:
    """An event failing ONLY on mover residual FAILs (§11-i dead-branch regression)."""
    row, b_home = _flicker_row()
    pe = project_event(row, coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0)
    assert pe.proj_report.mover_max_residual >= 0.5
    g3 = next(g for g in run_gates(pe, thresholds=_thresholds()) if g.gate == "G3")
    assert g3.outcome == GateOutcome.FAIL
    assert "MOVER_OFFLATTICE" in g3.detail


# --------------------------------------------------------------------------- #
# §11-ii — flicker atom is a mover: gated, not masked                         #
# --------------------------------------------------------------------------- #
def test_flicker_atom_registers_as_mover_and_is_gated_not_masked() -> None:
    row, b_home = _flicker_row()
    pe = project_event(row, coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0)
    # The flicker atom's site-change is ground truth: it is a detected mover.
    assert b_home in pe.movers
    # Its residual keys the gate (phantom-delta protection: discard, not mask) ...
    assert pe.proj_report.mover_max_residual == pytest.approx(1.15, abs=0.02)
    # ... and its context row is NOT masked (movers are gated, never masked).
    assert _ctx_kind(pe, b_home) == "SPECIES"
    # Through the installed driver the row lands in the ledger, not the catalogue.
    rep = ReftableBuildReport()
    events = project_reference_table(
        _FakeDF([row]), coloring=Coloring.FULL, rcut=5.0, d_max=2, r_ctx_min=3.0, report=rep
    )
    assert events == []
    assert rep.n_discarded == 1 and rep.n_mover_offlattice == 1
    assert rep.discarded[0].reason == "MOVER_OFFLATTICE"


# --------------------------------------------------------------------------- #
# §11-iii — §6 bystander masking                                              #
# --------------------------------------------------------------------------- #
def test_static_bystander_masked_to_wildcard() -> None:
    """A >= 0.5 A static bystander's context row demotes to WILDCARD (§6)."""
    pe, _ = _hop_event(bystander_shift_A=0.7)
    assert _ctx_kind(pe, (0, 2, 0)) == "WILDCARD"
    # G3 still PASSes: masking replaces gating for static bystanders.
    g3 = next(g for g in run_gates(pe, thresholds=_thresholds()) if g.gate == "G3")
    assert g3.outcome == GateOutcome.PASS


def test_below_threshold_bystander_not_masked() -> None:
    pe, _ = _hop_event(bystander_shift_A=0.3)
    assert _ctx_kind(pe, (0, 2, 0)) == "SPECIES"


def test_masking_never_touches_delta_or_empty_rows() -> None:
    pe, _ = _hop_event(bystander_shift_A=0.7)
    delta_offs = {ds.off for ds in pe.delta}
    assert delta_offs == {(0, 0, 0), (1, 1, 0)}
    # Delta sites keep their exact before-state claims (SPECIES origin, EMPTY target).
    assert _ctx_kind(pe, (0, 0, 0)) == "SPECIES"
    assert _ctx_kind(pe, (1, 1, 0)) == "EMPTY"
    # No EMPTY/OUTSIDE row anywhere was demoted (only occupied claims can be masked).
    for cs in pe.context:
        if cs.pred.kind == "WILDCARD":
            assert cs.off == (0, 2, 0)


def test_mask_changes_identity_and_depth_inputs() -> None:
    """The mask is applied BEFORE canonicalisation: identity encodes it (§6/§8.1)."""
    canonical = pytest.importorskip("pylatkmc.ingest.canonical")
    pe_masked, _ = _hop_event(bystander_shift_A=0.7)
    pe_unmasked, _ = _hop_event(bystander_shift_A=0.7, bystander_mask_tol=1.0e9)
    assert _ctx_kind(pe_unmasked, (0, 2, 0)) == "SPECIES"
    assert canonical.class_id(pe_masked) != canonical.class_id(pe_unmasked)
    # And a clean event is untouched by the mask machinery (same id either way).
    pe_a, _ = _hop_event()
    pe_b, _ = _hop_event(bystander_mask_tol=1.0e9)
    assert canonical.class_id(pe_a) == canonical.class_id(pe_b)


# --------------------------------------------------------------------------- #
# §11-iv — ledger conservation: n_rows = n_projected + n_raised + n_discarded #
# --------------------------------------------------------------------------- #
def _chain_row(idx_ref: int):
    """An unfittable 1-D chain -> FRAME_UNFIT (relocates to the ledger, §5)."""
    chain = np.asarray([[i * NN, 0.0, 0.0] for i in range(8)], dtype=float)
    return _row(
        initial_positions=chain,
        final_positions=chain,
        saddle_positions=chain,
        initial_types=["Ni"] * 8,
        move_atom_idx=0,
        idx_ref=idx_ref,
        source_row=idx_ref,
        event_id=f"chain{idx_ref}",
    )


def test_ledger_conservation_and_contents(tmp_path: Path) -> None:
    good_pe, good_row = _hop_event()
    good_row = dict(good_row, idx_ref=0, source_row=0)
    flicker, _ = _flicker_row(idx_ref=1)
    unfit = _chain_row(idx_ref=2)
    raising = _row(idx_ref=3)  # no positions at all -> raises inside project_event

    rep = ReftableBuildReport()
    events = project_reference_table(
        _FakeDF([good_row, flicker, unfit, raising]),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
        report=rep,
    )
    assert rep.n_rows == 4
    assert rep.n_projected == len(events) == 1
    assert len(rep.failures) == 1 and rep.failures[0][0] == 3
    assert rep.n_discarded == 2
    assert rep.n_mover_offlattice == 1 and rep.n_frame_unfit == 1
    # exact conservation (memo §5)
    assert rep.n_rows == rep.n_projected + len(rep.failures) + rep.n_discarded

    by_reason = {d.reason: d for d in rep.discarded}
    assert by_reason["MOVER_OFFLATTICE"].row == 1
    assert by_reason["MOVER_OFFLATTICE"].mover_max_residual == pytest.approx(1.15, abs=0.02)
    assert by_reason["FRAME_UNFIT"].row == 2
    assert math.isinf(by_reason["FRAME_UNFIT"].mover_max_residual)
    assert "orthogonal" in by_reason["FRAME_UNFIT"].detail
    # ledger rows are in row-position order (deterministic)
    assert [d.row for d in rep.discarded] == sorted(d.row for d in rep.discarded)

    # sidecar round-trip
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.reftable import write_discard_ledger_parquet

    out = tmp_path / "catalogue.parquet"
    ledger = discard_ledger_path(out)
    assert ledger == tmp_path / "catalogue_discarded.parquet"
    write_discard_ledger_parquet(rep.discarded, ledger)
    import pyarrow.parquet as pq

    table = pq.read_table(ledger)
    assert table.num_rows == 2
    got = table.to_pylist()
    assert [r["reason"] for r in got] == ["MOVER_OFFLATTICE", "FRAME_UNFIT"]
    assert got[1]["mover_max_residual"] is None  # inf -> null in parquet


def test_frame_unfit_never_reaches_catalogue() -> None:
    """FRAME_UNFIT rows relocate to the ledger (convention change vs 2026-07-22 §3.6)."""
    rep = ReftableBuildReport()
    events = project_reference_table(
        _FakeDF([_chain_row(0)]),
        coloring=Coloring.FULL,
        rcut=5.0,
        d_max=2,
        r_ctx_min=3.0,
        report=rep,
    )
    assert events == [] and rep.n_frame_unfit == 1
    assert rep.discarded[0].reason == "FRAME_UNFIT"


# --------------------------------------------------------------------------- #
# §11-vi — two-seed byte-determinism of catalogue + ledger                    #
# --------------------------------------------------------------------------- #
_DETERMINISM_SCRIPT = r"""
import hashlib, math, sys
import numpy as np
from pylatkmc.ingest.event_class import Coloring, GateThresholds, write_catalogue_parquet
from pylatkmc.ingest.reftable import (
    ReftableBuildReport, build_catalogue_from_reference_table,
    write_discard_ledger_parquet,
)

H = 1.76
NN = H * math.sqrt(2.0)

def ball(rad2):
    reach = int(math.isqrt(rad2)) + 1
    return sorted(
        (i, j, k)
        for i in range(-reach, reach + 1)
        for j in range(-reach, reach + 1)
        for k in range(-reach, reach + 1)
        if (i + j + k) % 2 == 0 and i * i + j * j + k * k <= rad2
    )

def cart(off):
    return H * np.asarray(off, dtype=float)

def hop_row(idx, shift):
    occ = {s: "Ni" for s in ball(8)}
    del occ[(1, 1, 0)]
    sites = sorted(occ)
    pos = np.asarray([cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    mi = sites.index((0, 0, 0))
    bi = sites.index((0, 2, 0))
    if shift:
        d = (cart((1, 3, 0)) - cart((0, 2, 0))) / NN
        pos = pos.copy(); pos[bi] = pos[bi] + shift * d
    P2 = pos.copy(); P2[mi] = cart((1, 1, 0))
    Psad = pos.copy(); Psad[mi] = 0.5 * (cart((0, 0, 0)) + cart((1, 1, 0)))
    return dict(
        initial_positions=pos, final_positions=P2, saddle_positions=Psad,
        initial_types=types, move_atom_idx=mi, energy_barrier=0.6 + 0.01 * idx,
        k=1e6, k_prefactor=1e13, id_saddle=f"s{idx}", id_final=f"f{idx}",
        event_id=f"e{idx}", idx_ref=idx, idx_backward=-1, source_row=idx, cell=None,
    )

class FakeDF:
    def __init__(self, rows):
        self.iloc = rows
    def __len__(self):
        return len(self.iloc)

rows = [hop_row(0, 0.0), hop_row(1, 0.7), hop_row(2, 0.7), hop_row(3, 0.3)]
th = GateThresholds(emin_event=0.0, emax_event=5.0, backward_emin_event=0.0, rcut=5.0)
rep = ReftableBuildReport()
classes = build_catalogue_from_reference_table(
    FakeDF(rows), coloring=Coloring.FULL, rcut=5.0, thresholds=th,
    t_ref_K=500.0, d_max=2, r_ctx_min=3.0, report=rep,
)
cat, led = sys.argv[1], sys.argv[2]
write_catalogue_parquet(classes, cat)
write_discard_ledger_parquet(rep.discarded, led)
print(hashlib.sha256(open(cat, "rb").read()).hexdigest())
print(hashlib.sha256(open(led, "rb").read()).hexdigest())
"""


def test_catalogue_and_ledger_bytes_deterministic_across_hashseed(tmp_path: Path) -> None:
    """Two PYTHONHASHSEED runs write byte-identical catalogue + ledger parquets."""
    pytest.importorskip("pyarrow")
    outputs = []
    for seed in ("0", "1"):
        cat = tmp_path / f"cat{seed}.parquet"
        led = tmp_path / f"led{seed}.parquet"
        env = dict(os.environ, PYTHONHASHSEED=seed)
        proc = subprocess.run(
            [sys.executable, "-c", _DETERMINISM_SCRIPT, str(cat), str(led)],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        outputs.append(proc.stdout)
    assert outputs[0] == outputs[1], "catalogue/ledger bytes differ across PYTHONHASHSEED"


# --------------------------------------------------------------------------- #
# §11-vii — ni_example proclist byte-identical (family-CSV path untouched)    #
# --------------------------------------------------------------------------- #
def test_ni_example_proclist_byte_identical(tmp_path: Path) -> None:
    """Regenerating ni_example reproduces the committed proclist.{c,h} exactly."""
    repo = Path(__file__).resolve().parents[2]
    spec_path = repo / "models" / "ni_example" / "ni_example.kmcspec.toml"
    from pylatkmc.codegen import generate
    from pylatkmc.loader import load

    spec = load(spec_path)
    written = generate(spec, tmp_path, spec_path=spec_path)
    committed_dir = repo / "models" / "ni_example" / "generated"
    for path in written:
        committed = committed_dir / path.name
        assert committed.is_file(), f"missing committed counterpart for {path.name}"
        a = hashlib.sha256(path.read_bytes()).hexdigest()
        b = hashlib.sha256(committed.read_bytes()).hexdigest()
        assert a == b, f"{path.name} drifted from the committed proclist"
