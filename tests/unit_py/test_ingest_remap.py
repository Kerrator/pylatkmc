"""Stamp-remap round-trip (over-snapping memo 2026-07-29 §11-v, §8.3).

A CANON bump relabels every ``class_id``; the ``remap`` step carries measured/
graduated stamps, veto overlays, and review lists across by event lineage. The
round-trip here fabricates one reference table with

* a **clean hop** (kept under any tolerance), stamped ``harvested_pair`` in the
  "old" catalogue -- the stamp must SURVIVE onto the class the member lands in
  under the new policy; and
* a **mover-off-lattice hop** (a 1.15 Å flicker mover; kept by the permissive
  old build at tol 1.5, discarded at the 0.5 Å mover gate), stamped
  ``pending_research`` -- the old class must be EXPLICITLY reported
  ``UNMATCHED_ALL_MEMBERS_DISCARDED`` with the ledger reason, never silently
  dropped.

Also locked: lineage keys on ``idx_ref`` alone (an ``idx_ref`` claimed twice in
the new build is a hard error; pairing the wrong reference table surfaces as
reported ``UNMATCHED_MEMBERS_MISSING``, never a silent no-op), veto-overlay +
review-list remapping through the same lineage (stray old ids reported), and
byte determinism of the CLI outputs across repeated invocations.
"""

from __future__ import annotations

import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from pylatkmc.ingest.event_class import Coloring, GateThresholds
from pylatkmc.ingest.qc import NU0_POLICY_HARVESTED_PAIR, NU0_POLICY_PENDING_RESEARCH
from pylatkmc.ingest.reftable import (
    ReftableBuildReport,
    build_catalogue_from_reference_table,
)
from pylatkmc.ingest.remap import (
    OUTCOME_DISCARDED,
    OUTCOME_REMAPPED,
    apply_stamps,
    build_lineage,
    remap_classes,
    remap_payload,
)

H = 1.76  # half spacing a/2 for a = 3.52 A
NN = H * math.sqrt(2.0)


# --------------------------------------------------------------------------- #
# Synthetic corpus (house style of test_ingest_oversnap)                      #
# --------------------------------------------------------------------------- #
def _ball_sites(rad2: int) -> list[tuple[int, int, int]]:
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
    return H * np.asarray(off, dtype=float)


def _row_fields(idx_ref: int, **kw) -> dict:
    base = dict(
        energy_barrier=0.6,
        k=1.0e6,
        k_prefactor=1.0e13,
        id_saddle="s",
        id_final="f",
        event_id=f"e{idx_ref}",
        idx_ref=idx_ref,
        idx_backward=-1,
        source_row=idx_ref,
        cell=None,
    )
    base.update(kw)
    return base


def _hop_row(idx_ref: int) -> dict:
    """A clean Ni hop into the (1,1,0) vacancy — kept under any tolerance."""
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    mi = sites.index((0, 0, 0))
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    Psad = pos.copy()
    Psad[mi] = 0.5 * (pos[mi] + _cart((1, 1, 0)))
    return _row_fields(
        idx_ref,
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
    )


def _offlattice_row(idx_ref: int) -> dict:
    """A hop whose flicker atom is a 1.15 Å off-lattice mover (house style of
    ``test_ingest_oversnap._flicker_row``).

    Atom B sits 1.15 Å out of its home site in P0 (still snaps home) and
    1.35 Å out in P2 (snaps to the adjacent vacancy): a site-assignment flip,
    so B is a mover with snap residual 1.15 Å — kept by the permissive "old"
    build (tol 1.5), dropped to the ledger by the 0.5 Å gate. The second
    vacancy also makes the context (hence ``class_id``) differ from the clean
    hop.
    """
    occ = {s: "Ni" for s in _ball_sites(8)}
    del occ[(1, 1, 0)]  # seed's vacancy target
    del occ[(1, -1, 2)]  # the flicker atom's adjacent empty site
    b_home = (0, 0, 2)
    sites = sorted(occ)
    pos = np.asarray([_cart(s) for s in sites], dtype=float)
    types = [occ[s] for s in sites]
    mi = sites.index((0, 0, 0))
    bi = sites.index(b_home)
    direction = (_cart((1, -1, 2)) - _cart(b_home)) / NN
    pos = pos.copy()
    pos[bi] = _cart(b_home) + 1.15 * direction
    P2 = pos.copy()
    P2[mi] = _cart((1, 1, 0))
    P2[bi] = _cart(b_home) + 1.35 * direction
    Psad = pos.copy()
    Psad[mi] = 0.5 * (_cart((0, 0, 0)) + _cart((1, 1, 0)))
    return _row_fields(
        idx_ref,
        initial_positions=pos,
        final_positions=P2,
        saddle_positions=Psad,
        initial_types=types,
        move_atom_idx=mi,
        event_id=f"flicker{idx_ref}",
    )


class _FakeDF:
    def __init__(self, rows):
        self.iloc = rows

    def __len__(self) -> int:
        return len(self.iloc)


def _thresholds(mover_snap_tol: float) -> GateThresholds:
    return GateThresholds(
        emin_event=0.0,
        emax_event=5.0,
        backward_emin_event=0.0,
        rcut=5.0,
        mover_snap_tol=mover_snap_tol,
        bystander_mask_tol=1.5,
    )


def _build(mover_snap_tol: float) -> tuple[list, ReftableBuildReport]:
    df = _FakeDF([_hop_row(0), _offlattice_row(1)])
    report = ReftableBuildReport()
    classes = build_catalogue_from_reference_table(
        df,
        coloring=Coloring.FULL,
        rcut=5.0,
        thresholds=_thresholds(mover_snap_tol),
        t_ref_K=500.0,
        d_max=2,
        r_ctx_min=3.0,
        report=report,
    )
    return classes, report


def _stamped_old() -> list:
    """The 'old' permissive-tolerance catalogue with both classes stamped."""
    old, report = _build(mover_snap_tol=1.5)
    assert report.n_discarded == 0 and len(old) == 2
    stamped = []
    for c in old:
        if 0 in c.source_rows:
            stamped.append(
                dataclasses.replace(
                    c,
                    nu0_pair_policy=NU0_POLICY_HARVESTED_PAIR,
                    audit_reason="graduated 2026-07-23 (research agrees within band)",
                )
            )
        else:
            stamped.append(dataclasses.replace(c, nu0_pair_policy=NU0_POLICY_PENDING_RESEARCH))
    return stamped


def _ledger_dicts(report: ReftableBuildReport) -> list[dict]:
    return [dataclasses.asdict(d) for d in report.discarded]


# --------------------------------------------------------------------------- #
# §11-v — the round-trip                                                      #
# --------------------------------------------------------------------------- #
def test_stamp_survives_and_unmatched_is_reported() -> None:
    old = _stamped_old()
    new, new_report = _build(mover_snap_tol=0.5)
    assert new_report.n_discarded == 1 and len(new) == 1

    lineage = build_lineage(new, _ledger_dicts(new_report))
    report = remap_classes(old, lineage)
    counts = report.counts()
    assert counts["old_classes"] == 2
    assert counts["old_stamped"] == 2
    assert counts[OUTCOME_REMAPPED] == 1
    assert counts[OUTCOME_DISCARDED] == 1
    assert counts["old_stamped_unmatched"] == 1

    by_outcome = {cr.outcome: cr for cr in report.classes}
    survived = by_outcome[OUTCOME_REMAPPED]
    assert survived.old_policy == NU0_POLICY_HARVESTED_PAIR
    assert survived.new_class_ids == (new[0].class_id,)
    unmatched = by_outcome[OUTCOME_DISCARDED]
    assert unmatched.old_policy == NU0_POLICY_PENDING_RESEARCH
    assert unmatched.new_class_ids == ()
    assert unmatched.discard_reasons == ("MOVER_OFFLATTICE",)

    stamped = apply_stamps(new, report, note="migration test")
    assert stamped[0].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert survived.old_class_id[:12] in stamped[0].audit_reason
    assert "graduated 2026-07-23" in stamped[0].audit_reason
    assert "migration test" in stamped[0].audit_reason


def test_wrong_corpus_surfaces_as_missing_not_silence() -> None:
    old = _stamped_old()
    new, new_report = _build(mover_snap_tol=0.5)
    tampered = [
        dataclasses.replace(c, source_idx_refs=tuple(i + 7 for i in c.source_idx_refs)) for c in old
    ]
    lineage = build_lineage(new, _ledger_dicts(new_report))
    report = remap_classes(tampered, lineage)
    assert all(cr.outcome == "UNMATCHED_MEMBERS_MISSING" for cr in report.classes)
    assert report.counts()["old_stamped_unmatched"] == 2


def test_doubly_claimed_idx_ref_is_a_hard_error() -> None:
    new, new_report = _build(mover_snap_tol=0.5)
    ledger = _ledger_dicts(new_report)
    duplicate = [dict(ledger[0], idx_ref=int(new[0].source_idx_refs[0]))]
    with pytest.raises(ValueError, match="corrupt new build"):
        build_lineage(new, duplicate)


def test_overlay_remap_reports_unmatched_and_stray_ids() -> None:
    old = _stamped_old()
    new, new_report = _build(mover_snap_tol=0.5)
    report = remap_classes(old, build_lineage(new, _ledger_dicts(new_report)))
    survived = next(cr for cr in report.classes if cr.outcome == OUTCOME_REMAPPED)
    dropped = next(cr for cr in report.classes if cr.outcome == OUTCOME_DISCARDED)

    payload = {
        survived.old_class_id: "frozen: veto A",
        dropped.old_class_id: "unreachable: veto B",
        "deadbeef" * 8: "stray entry",
    }
    new_payload, records = remap_payload(payload, report, note="mig")
    assert set(new_payload) == {new[0].class_id}
    assert "veto A" in new_payload[new[0].class_id]
    assert survived.old_class_id[:12] in new_payload[new[0].class_id]
    outcomes = {r[0]: r[1] for r in records}
    assert outcomes[dropped.old_class_id] == OUTCOME_DISCARDED
    assert outcomes["deadbeef" * 8] == "UNMATCHED_NOT_IN_OLD_CATALOGUE"


# --------------------------------------------------------------------------- #
# CLI round-trip (parquet + overlay TOML + review CSV), byte-deterministic    #
# --------------------------------------------------------------------------- #
def _run_cli_remap(tmp: Path, old_pq: Path, new_pq: Path, overlay_in: Path, review_in: Path):
    from pylatkmc.ingest.cli import main

    out = tmp / "stamped.parquet"
    rep = tmp / "report.csv"
    ov = tmp / "vetoes_v2.toml"
    rv = tmp / "review_v2.csv"
    rc = main(
        [
            "remap",
            "--old",
            str(old_pq),
            "--new",
            str(new_pq),
            "--out",
            str(out),
            "--report",
            str(rep),
            "--overlay-in",
            str(overlay_in),
            "--overlay-out",
            str(ov),
            "--review-in",
            str(review_in),
            "--review-out",
            str(rv),
            "--note",
            "CANON v2 migration test",
            "--conditions",
            "remap round-trip fixture",
        ]
    )
    assert rc == 0
    return out, rep, ov, rv


def test_cli_remap_round_trip_and_determinism(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.event_class import read_catalogue_parquet, write_catalogue_parquet
    from pylatkmc.ingest.qc import load_overlay
    from pylatkmc.ingest.reftable import discard_ledger_path, write_discard_ledger_parquet

    old = _stamped_old()
    new, new_report = _build(mover_snap_tol=0.5)
    old_pq = tmp_path / "old.parquet"
    new_pq = tmp_path / "new.parquet"
    write_catalogue_parquet(old, old_pq)
    write_catalogue_parquet(new, new_pq)
    write_discard_ledger_parquet(new_report.discarded, discard_ledger_path(new_pq))

    survived_old = next(c for c in old if 0 in c.source_rows)
    dropped_old = next(c for c in old if 1 in c.source_rows)
    overlay_in = tmp_path / "vetoes_old.toml"
    overlay_in.write_text(
        f'"{survived_old.class_id}" = "frozen: veto A"\n'
        f'"{dropped_old.class_id}" = "unreachable: veto B"\n'
    )
    review_in = tmp_path / "review_old.csv"
    review_in.write_text(
        "idx_ref,class_id,review_reason\n"
        f"0,{survived_old.class_id},token-flicker\n"
        f"1,{dropped_old.class_id},structural\n"
    )

    runs = []
    for sub in ("a", "b"):
        d = tmp_path / sub
        d.mkdir()
        runs.append(_run_cli_remap(d, old_pq, new_pq, overlay_in, review_in))

    out, rep, ov, rv = runs[0]
    stamped = read_catalogue_parquet(out)
    assert stamped[0].nu0_pair_policy == NU0_POLICY_HARVESTED_PAIR
    assert survived_old.class_id[:12] in stamped[0].audit_reason

    report_text = rep.read_text()
    assert "UNMATCHED_ALL_MEMBERS_DISCARDED" in report_text
    assert "MOVER_OFFLATTICE" in report_text
    assert dropped_old.class_id in report_text

    remapped_overlay = load_overlay(ov)
    assert set(remapped_overlay) == {new[0].class_id}
    assert "veto A" in remapped_overlay[new[0].class_id]

    review_text = rv.read_text()
    assert f"{new[0].class_id}" in review_text
    assert "UNMATCHED_ALL_MEMBERS_DISCARDED" in review_text

    # byte determinism across invocations (report/overlay/review + parquet)
    for i in range(4):
        assert runs[0][i].read_bytes() == runs[1][i].read_bytes(), runs[0][i].name
