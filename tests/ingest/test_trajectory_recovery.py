"""Unit tests for the deterministic parts of trajectory-recovery HTST.

These cover the pure-logic pipeline (cadence, provenance aggregation, target
resolution, mover detection, free-region auto-freeze, idempotent upsert) without
invoking LAMMPS. The ν₀ Hessian step is validated separately against the anchor
family (surface_1NN_inplane ≈ canonical 13.13 THz) in the integration runner.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pylatkmc.ingest import trajectory_recovery as tr
from pylatkmc.ingest.cadence import Cadence, count_xyz_frames, parse_sample_every
from pylatkmc.ingest.provenance import (
    BucketRecord,
    GeometryRecord,
    RecoveryStatus,
)


# --------------------------------------------------------------------------- #
# Cadence
# --------------------------------------------------------------------------- #
def test_cadence_1to1_frame_before_step():
    cad = Cadence(sample_every=1, n_frames=2001, max_step=2000)
    assert cad.step_on_cadence(7)
    # min1 of the event at step N is frame N-1 for 1:1 cadence
    assert cad.frame_before_step(1) == 0
    assert cad.frame_before_step(2000) == 1999
    assert cad.frame_before_step(0) is None  # no frame before step 0


def test_cadence_subsampled():
    cad = Cadence(sample_every=10, n_frames=11, max_step=100)
    assert cad.step_on_cadence(20)
    assert not cad.step_on_cadence(23)
    # frame_before_step needs (step-1) on cadence
    assert cad.frame_before_step(11) == 1  # prev=10 -> frame 1
    assert cad.frame_before_step(15) is None  # prev=14 off-cadence
    assert cad.frame_before_step(10000) is None  # out of range


def test_parse_sample_every(tmp_path):
    p = tmp_path / "input.in"
    p.write_text("[run]\nmax_steps = 100\nsample_every = 5\n")
    assert parse_sample_every(p) == 5
    p2 = tmp_path / "input2.in"
    p2.write_text("[run]\nmax_steps = 100\n")  # absent -> default 1
    assert parse_sample_every(p2) == 1
    assert parse_sample_every(tmp_path / "missing.in") == 1


def test_count_xyz_frames(tmp_path):
    p = tmp_path / "traj.xyz"
    frame = "2\ncomment\nNi 0.0 0.0 0.0\nNi 1.0 1.0 1.0\n"
    p.write_text(frame * 3)
    assert count_xyz_frames(p) == 3


# --------------------------------------------------------------------------- #
# Provenance aggregation
# --------------------------------------------------------------------------- #
def _geo(nu0, status=RecoveryStatus.OK):
    return GeometryRecord(
        family_id="surface_1NN_inplane", family_bucket_id="nv1=0_nv2=0",
        sim_path="/x", idx_ref=1, status=status, nu0_Hz=nu0,
    )


def test_bucket_median_and_geomean():
    b = BucketRecord("surface_1NN_inplane", "nv1=0_nv2=0", 500.0)
    b.geometries = [_geo(10e12), _geo(20e12), _geo(30e12),
                    _geo(99e12, RecoveryStatus.NU0_OUT_OF_RANGE)]  # excluded
    assert b.n_attempted == 4
    assert b.n_accepted == 3
    assert b.nu0_median() == pytest.approx(20e12)
    assert b.nu0_geomean() == pytest.approx((10e12 * 20e12 * 30e12) ** (1 / 3))
    row = b.to_row()
    assert row["nu0_source"] == "trajectory"
    assert row["n_geos_accepted"] == 3


def test_bucket_no_accepted_is_none():
    b = BucketRecord("f", "b", 500.0)
    b.geometries = [_geo(None, RecoveryStatus.EVENT_NEVER_FIRED)]
    assert b.nu0_median() is None
    assert b.to_row()["nu0_source"] == "none"


def test_geometry_record_ok_property():
    assert _geo(15e12).ok
    assert not _geo(None, RecoveryStatus.ERROR).ok
    assert not _geo(15e12, RecoveryStatus.NU0_OUT_OF_RANGE).ok


# --------------------------------------------------------------------------- #
# Target resolution
# --------------------------------------------------------------------------- #
def test_resolve_targets(tmp_path):
    classified = pd.DataFrame({
        "sim_path": ["/sim/a", "/sim/b", "/sim/c"],
        "idx_ref": [10, 20, 30],
        "n_moved": [1, 1, 2],
        "family_id": ["surface_1NN_inplane"] * 3,
    })
    cpath = tmp_path / "classified.csv"
    classified.to_csv(cpath, index=False)

    rate = pd.DataFrame({
        "family_id": ["surface_1NN_inplane", "bulk_1NN_inplane"],
        "family_bucket_id": ["nv1=0_nv2=0", "nv1=0"],
        "n_events": [3, 0],  # bulk has 0 events -> skipped
        "representative_row_indices": [json.dumps([0, 2]), json.dumps([1])],
    })
    rpath = tmp_path / "rate.csv"
    rate.to_csv(rpath, index=False)

    targets = tr.resolve_targets(rpath, cpath)
    assert len(targets) == 2  # only the surface family (bulk skipped: n_events=0)
    assert {t.idx_ref for t in targets} == {10, 30}
    assert targets[0].sim_path == "/sim/a"
    assert targets[1].n_moved == 2

    # family filter
    only = tr.resolve_targets(rpath, cpath, families=["bulk_1NN_inplane"])
    assert only == []  # bulk has n_events=0


# --------------------------------------------------------------------------- #
# Mover detection (PBC-corrected frame diff)
# --------------------------------------------------------------------------- #
def test_detect_movers_single_hop():
    from ase import Atoms

    pos = np.array([[0, 0, 0], [3, 0, 0], [0, 3, 0], [3, 3, 0]], dtype=float)
    f0 = Atoms("Ni4", positions=pos, cell=[10, 10, 10], pbc=True)
    pos1 = pos.copy()
    pos1[2] += [0.0, 0.7, 0.0]  # atom 2 hops 0.7 Å
    f1 = Atoms("Ni4", positions=pos1, cell=[10, 10, 10], pbc=True)
    ms = tr.detect_movers(f0, f1)
    assert ms is not None
    assert ms.primary == 2
    assert ms.movers == (2,)
    assert ms.max_disp_A == pytest.approx(0.7)


def test_detect_movers_pbc_wrap():
    from ase import Atoms

    # atom near the cell edge wraps across the boundary: raw diff ~ -9.5 Å,
    # min-image displacement ~ +0.5 Å (below threshold -> no mover)
    f0 = Atoms("Ni1", positions=[[9.8, 0, 0]], cell=[10, 10, 10], pbc=True)
    f1 = Atoms("Ni1", positions=[[0.3, 0, 0]], cell=[10, 10, 10], pbc=True)
    ms = tr.detect_movers(f0, f1)
    assert ms is None  # 0.5 Å min-image displacement is below the 0.5 threshold floor


def test_detect_movers_none_when_static():
    from ase import Atoms

    f = Atoms("Ni2", positions=[[0, 0, 0], [2, 0, 0]], cell=[10, 10, 10], pbc=True)
    assert tr.detect_movers(f, f) is None


# --------------------------------------------------------------------------- #
# Free-region selection + auto-freeze
# --------------------------------------------------------------------------- #
def test_free_region_subsurface_mover_keeps_full_region():
    # mover at z=0 is SUBSURFACE (top atom at z=+2): auto-freeze must NOT fire,
    # so the atom above stays free (the subsurface_1NN saddle-truncation fix).
    pos = np.array([
        [0.0, 0.0, 0.0],   # mover (idx 0), subsurface
        [1.0, 0.0, 0.0],   # same layer
        [0.0, 0.0, 2.0],   # above mover -> KEPT (no auto-freeze for subsurface)
        [0.0, 0.0, -1.0],  # below mover
    ])
    free = tr._free_region(pos, move_atom_idx=0, free_radius=6.0, auto_freeze_above_mover=True)
    assert set(free.tolist()) == {0, 1, 2, 3}  # full radial region, nothing frozen


def test_free_region_surface_mover_clean_is_noop():
    # A clean surface mover IS the top layer (nothing above), so auto-freeze is
    # a no-op: True and False give the same full region. (An atom genuinely above
    # would itself be the top layer, making the mover subsurface — so the freeze
    # branch never truncates a real surface hop; the frozen rcut boundary handles
    # surface soft modes.)
    pos = np.array([
        [0.0, 0.0, 0.0],   # mover (idx 0), top layer
        [1.0, 0.0, 0.0],   # same layer
        [0.0, 0.0, -1.0],  # subsurface
        [1.0, 0.0, -1.0],  # subsurface
    ])
    free_on = tr._free_region(pos, 0, 6.0, auto_freeze_above_mover=True)
    free_off = tr._free_region(pos, 0, 6.0, auto_freeze_above_mover=False)
    assert set(free_on.tolist()) == set(free_off.tolist()) == {0, 1, 2, 3}


# --------------------------------------------------------------------------- #
# Idempotent CSV upsert
# --------------------------------------------------------------------------- #
def test_upsert_replaces_and_appends(tmp_path):
    p = tmp_path / "out.csv"
    tr._upsert(p, [{"family_id": "f1", "T_K": 500, "nu0_Hz": 1.0}], keys=("family_id", "T_K"))
    tr._upsert(p, [{"family_id": "f1", "T_K": 500, "nu0_Hz": 2.0},   # replace
                   {"family_id": "f2", "T_K": 500, "nu0_Hz": 3.0}],  # append
               keys=("family_id", "T_K"))
    df = pd.read_csv(p)
    assert len(df) == 2  # no duplicate (f1,500)
    assert df.loc[df.family_id == "f1", "nu0_Hz"].iloc[0] == 2.0
    assert set(df.family_id) == {"f1", "f2"}
