"""Phase C E_sym surrogate tests: feature ports, ridge/leverage, model I/O, stamping.

Four tiers:

- **Always-run synthetic** (numpy only): a real ``build_class_catalogue`` EventClass with
  pinned literal ``sym_features`` / ``dphi2`` / ``phi_vector``; the ``H2FEATS`` order pinned
  as a literal; the closed 115-key basis reconstructed from its defining rule; ridge fit +
  leverage on a tiny fixed matrix with hardcoded expected outputs; ``EsymModel`` JSON
  round-trip; ``phi_vector`` unknown-key raise.
- **v2 category alphabet** (blockers B2 + B3): WILDCARD/OCC_ANY → ``"W"``, Fe → ``"F"``,
  an unknown species raising, and the F/W zero-contribution semantics of ΔΦ.
- **C index lockstep**: the phi index helpers in ``runtime/src/core/surrogate.{c,h}`` are
  parsed from source and checked against the pinned Python basis — no compiler needed.
- **Stamping** (pyarrow-guarded): stamp a synthetic mini-catalogue, round-trip the Parquet,
  assert the [C] fields (``phi`` / versions / ``fallback_stats``) and ``schema_version`` survive.
- **Production pinned vectors** (skips without the machine-local QC'd Parquet): four known
  class_ids spanning clean-hop Ni/Cr and multi-site Ni/Cr, asserted to still carry their
  **v1** 68-key values under the v2 superset basis (the port-fidelity anchor).

The feature literals were computed once against the verbatim 2026-07-21 script definitions
and hardcoded here; ``test_v2_is_v1_plus_dummies`` / ``test_production_pinned_vectors``
keep the v2 basis honest against them.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import numpy as np
import pytest

from pylatkmc.ingest import surrogate as S
from pylatkmc.ingest.event_class import (
    CATALOGUE_SCHEMA_VERSION,
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    EventProjReport,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
    build_class_catalogue,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_QC_PARQUET = REPO_ROOT / ".scratch/phaseC/catalogue_qc_rcut8p5.parquet"

_THRESHOLDS = GateThresholds(
    emin_event=0.0, emax_event=10.0, backward_emin_event=0.0, snap_tol=0.9, db_tol=0.05, rcut=5.0
)


def _sp(occ: Occ) -> OccPredicate:
    return OccPredicate("SPECIES", frozenset({occ}))


def _synth_class() -> EventClass:
    """A Cr 1NN in-plane surface hop with five context rows, via the REAL assembler."""
    pe = ProjectedEvent(
        anchor0=(0, 0, 0),
        delta=(
            DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.CR),
        ),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _sp(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), _sp(Occ.NI)),
            StencilSite((1, -1, 0), _sp(Occ.NI)),
            StencilSite((0, 2, 0), _sp(Occ.NI)),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.CR),),
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        coloring=Coloring.FULL,
        r_ctx_used=5.0,
        truncated=False,
        Ea_fwd_eV=0.6,
        nu0_fwd_hz=1.0e13,
        k_row=1.0,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        move_atom_idx=0,
        source_row=0,
        proj_report=EventProjReport(0.3, 0.2, 6.0, True),
    )
    return build_class_catalogue(
        [pe], t_ref_K=500.0, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )[0]


# ---------------------------------------------------------------------------
# Synthetic feature ports — pinned literals
# ---------------------------------------------------------------------------

#: The v1 (68-key basis) ``sym_features`` literal for the synthetic class, kept
#: verbatim as the port-fidelity anchor. On a class with no Fe and no WILDCARD the
#: v2 basis must reproduce it EXACTLY — the only permitted deviation is the two
#: mover-species dummies (ruling 2026-08-15c). See test_v2_is_v1_plus_dummies.
_SYNTH_SYM_V1 = {
    "abs_delta_atoms": 0,
    "b_CE": 1.0,
    "b_CN": 1.5,
    "b_EN": 1.5,
    "b_NN": 1.0,
    "depth_param": 8,
    "depth_surface": 1,
    "mvC_E": 1.0,
    "mvC_N": 1.5,
    "n_delta": 2,
    "s0_C": 0.5,
    "s0_E": 0.5,
    "s0_N": 1.0,
    "s1_N": 2.0,
    "s9_C": 0.5,
    "s9_E": 0.5,
}

#: The v2 deviation: exactly these two keys, and nothing else.
_V2_EXTRA_KEYS = ("mover_n_C", "mover_n_F")

_SYNTH_SYM = {**_SYNTH_SYM_V1, "mover_n_C": 1.0, "mover_n_F": 0.0}

_SYNTH_DPHI2 = (
    0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0, 1.0,
)

#: The pinned v2 115-vector. Order is load-bearing: the C runtime's
#: PHI_*/SHELL_IDX/BOND_IDX/TRI_BASE constants index into exactly this layout.
_SYNTH_PHI = (
    0.0, 0.0, 1.0, 0.0, 1.5, 0.0, 0.0, 1.5, 0.0,
    0.0, 1.0, 8.0, 1.0, 1.0, 0.0, 0.0, 1.0, 0.0,
    1.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.5, 0.5,
    0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
)


def test_sym_features_synthetic_pinned() -> None:
    """The symmetrized E_sym dict of a known synthetic class matches the pinned literal."""
    assert S.sym_features(_synth_class()) == _SYNTH_SYM


def test_v2_is_v1_plus_dummies() -> None:
    """Port fidelity: on an Fe-free / wildcard-free class the v2 basis == v1 exactly.

    The original port-fidelity check asserted ``sym_features`` was byte-equal to the
    2026-07-21 ``esym_v1v3v5`` script over 439 classes. That script is a machine-local
    flat driver (it loads a catalogue at import), so the equality is anchored here
    instead against its pinned output for the synthetic class. The two mover-species
    dummies are a DELIBERATE v2 deviation (ruling 2026-08-15c); everything else —
    every shell, bond, mover-neighbour and triangle count — must be untouched.
    """
    f = S.sym_features(_synth_class())
    assert {k: v for k, v in f.items() if k not in _V2_EXTRA_KEYS} == _SYNTH_SYM_V1
    assert sorted(set(f) - set(_SYNTH_SYM_V1)) == sorted(_V2_EXTRA_KEYS)


def test_dphi2_synthetic_pinned() -> None:
    """The surfsplit ΔΦ vector of the synthetic class matches the pinned literal (18 entries).

    Unchanged from v1: the H(σ) basis is not touched by the v2 bump.
    """
    v = S.dphi2(_synth_class())
    assert v.shape == (18,)
    assert tuple(v.tolist()) == _SYNTH_DPHI2


def test_phi_vector_synthetic_pinned() -> None:
    """phi_vector emits the pinned-order 115-vector; equals sym_features read by key."""
    phi = S.phi_vector(_synth_class())
    assert len(phi) == 115
    assert phi == _SYNTH_PHI


def test_h2feats_order_pinned() -> None:
    """The H(σ) v2 surfsplit feature order is byte-stable (index contract into theta)."""
    assert S.H2FEATS == (
        "pt_NI", "pt_CR",
        "b1B_NN", "b1B_NC", "b1B_CC", "b1S_NN", "b1S_NC", "b1S_CC",
        "b2B_NN", "b2B_NC", "b2B_CC", "b2S_NN", "b2S_NC", "b2S_CC",
        "b1_NU", "b1_CU", "b2_NU", "b2_CU",
    )
    assert len(S.H2FEATS) == 18
    assert S.H2IDX["pt_NI"] == 0 and S.H2IDX["b2_CU"] == 17


def test_esym_feature_keys_pinned_length() -> None:
    """The pinned E_sym basis is the closed 115-key v2 alphabet, sorted."""
    assert len(S.ESYM_FEATURE_KEYS) == 115
    assert list(S.ESYM_FEATURE_KEYS) == sorted(S.ESYM_FEATURE_KEYS)
    assert S.ESYM_FEATURE_KEYS[0] == "abs_delta_atoms"
    assert S.ESYM_FEATURE_KEYS[-1] == "t3_WW"
    assert len(set(S.ESYM_FEATURE_KEYS)) == 115


def test_esym_basis_reconstructed_from_closed_rule() -> None:
    """The pinned literal is EXACTLY the closed-form basis over the 6-cat alphabet.

    Reconstructing it from the rule (rather than from the corpus) is what makes the
    basis future-proof: a NiFe or wildcard-heavy catalogue can be stamped without
    tripping phi_vector's unknown-key guard, and the guard still catches real bugs.
    """
    cats = S.CATEGORIES
    assert cats == ("C", "E", "F", "N", "U", "W")
    bondable = tuple(c for c in cats if c not in S.UNKNOWN_CATS)
    assert bondable == ("C", "E", "F", "N")

    keys = ["abs_delta_atoms", "depth_param", "depth_surface", "n_delta",
            "mover_n_C", "mover_n_F"]
    keys += [f"s{sh}_{c}" for sh in range(10) for c in cats]
    keys += ["b_" + "".join(p) for p in itertools.combinations_with_replacement(bondable, 2)]
    keys += [f"mv{m}_{c}" for m in S.OCCUPIED_CATS for c in cats]
    keys += ["t3_" + "".join(p) for p in itertools.combinations_with_replacement(cats, 2)]

    assert len(keys) == len(set(keys)) == 115
    assert tuple(sorted(keys)) == S.ESYM_FEATURE_KEYS
    # group sizes, spelled out (6 scalars + 60 shells + 10 bonds + 18 mv + 21 t3)
    assert sum(1 for k in S.ESYM_FEATURE_KEYS if k.startswith("s") and "_" in k[:3]) == 60
    assert sum(1 for k in S.ESYM_FEATURE_KEYS if k.startswith("b_")) == 10
    assert sum(1 for k in S.ESYM_FEATURE_KEYS if k.startswith("mv")) == 18
    assert sum(1 for k in S.ESYM_FEATURE_KEYS if k.startswith("t3_")) == 21


# ---------------------------------------------------------------------------
# v2 category alphabet: WILDCARD/OCC_ANY -> "W", Fe -> "F" (blockers B2 + B3)
# ---------------------------------------------------------------------------


def test_occ_cat_wildcard_and_occ_any_are_W() -> None:
    """WILDCARD and OCC_ANY map to the distinct "W" category — no raise, not "U".

    Before B2 these hit the single-element ``(sp,) = pred.species`` unpack and blew
    up, which is why any catalogue built after the 2026-07-29 over-snap memo (which
    masks ≥0.5 Å static bystanders to WILDCARD) could not be stamped at all.
    """
    assert S.occ_cat(OccPredicate("WILDCARD")) == "W"
    assert S.occ_cat(OccPredicate("OCC_ANY")) == "W"
    assert S.occ_cat(OccPredicate("OUTSIDE")) == "U"
    assert S.occ_cat(OccPredicate("EMPTY")) == "E"


def test_occ_cat_species_by_name() -> None:
    """Ni/Cr/Fe map to N/C/F by NAME (B3: Fe was silently folded into Cr in v1)."""
    assert S.occ_cat(_sp(Occ.NI)) == "N"
    assert S.occ_cat(_sp(Occ.CR)) == "C"
    assert S.occ_cat(_sp(Occ.FE)) == "F"
    assert S.OCCC["FE"] == "F"


def test_occ_cat_unknown_species_raises() -> None:
    """A species with no category raises loudly, naming it (never silently folded)."""

    class _FakeSp:
        name = "MO"

    with pytest.raises(ValueError, match="no E_sym category for species 'MO'"):
        S.occ_cat(OccPredicate("SPECIES", frozenset({_FakeSp()})))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="exactly one species"):
        S.occ_cat(OccPredicate("SPECIES", frozenset({Occ.NI, Occ.CR})))


def _wildcard_fe_class() -> EventClass:
    """An Fe 1NN hop whose context carries a WILDCARD and an OCC_ANY bystander."""
    pe = ProjectedEvent(
        anchor0=(0, 0, 0),
        delta=(
            DeltaSite((0, 0, 0), Occ.FE, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.FE),
        ),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _sp(Occ.FE)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), _sp(Occ.NI)),
            StencilSite((1, -1, 0), _sp(Occ.CR)),
            StencilSite((0, 2, 0), OccPredicate("WILDCARD")),
            StencilSite((2, 2, 0), OccPredicate("OCC_ANY")),
            # 1NN of the mover AND of the vacancy (1,1,0) -> gives a W triangle
            StencilSite((1, 0, 1), OccPredicate("WILDCARD")),
            StencilSite((0, 0, 2), OccPredicate("OUTSIDE")),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.FE),),
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        coloring=Coloring.FULL,
        r_ctx_used=5.0,
        truncated=False,
        Ea_fwd_eV=0.6,
        nu0_fwd_hz=1.0e13,
        k_row=1.0,
        id_saddle="s",
        id_final="f",
        event_id="e",
        idx_ref=0,
        idx_backward=-1,
        move_atom_idx=0,
        source_row=0,
        proj_report=EventProjReport(0.3, 0.2, 6.0, True),
    )
    return build_class_catalogue(
        [pe], t_ref_K=500.0, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )[0]


def test_state_maps_wildcard_and_fe() -> None:
    """The before/after maps carry W for masked bystanders and F for the Fe mover.

    Offsets are read off the (canonicalised, hence re-oriented) delta rather than
    hard-coded — the point under test is the category alphabet, not the orbit rep.
    """
    cls = _wildcard_fe_class()
    before, after = S.state_maps(cls)
    assert sorted(set(before.values())) == ["C", "E", "F", "N", "U", "W"]
    src = next(d.off for d in cls.delta if d.before.name == "FE")
    dst = next(d.off for d in cls.delta if d.after.name == "FE")
    assert before[src] == "F" and after[src] == "E"
    assert before[dst] == "E" and after[dst] == "F"
    # both masked bystanders (WILDCARD and OCC_ANY) and the OUTSIDE row survive
    assert sum(v == "W" for v in before.values()) == 3
    assert sum(v == "U" for v in before.values()) == 1


def test_sym_features_wildcard_fe_class() -> None:
    """A WILDCARD + Fe class produces s*_W / b_*F / mvF_* / mover_n_F and no unknown key."""
    cls = _wildcard_fe_class()
    f = S.sym_features(cls)

    assert f["mover_n_F"] == 1.0
    assert f["mover_n_C"] == 0.0
    # W sites carry their own shell label ...
    assert any(k.endswith("_W") and k.startswith("s") and v > 0 for k, v in f.items())
    # ... and their own mover-neighbour + triangle labels (Fe mover at the origin) ...
    assert f.get("mvF_W", 0.0) > 0.0
    assert any(k.startswith("t3_") and "W" in k and v > 0 for k, v in f.items())
    # ... but never a bond (W is structurally U).
    assert not any(k.startswith("b_") and "W" in k for k in f)
    # Fe is a real bonding species.
    assert f.get("b_CF", 0.0) + f.get("b_EF", 0.0) + f.get("b_FN", 0.0) > 0.0
    # mvF_* exists: Fe is an occupied mover (v1 skipped it entirely)
    assert any(k.startswith("mvF_") and v > 0 for k, v in f.items())
    assert not any(k.startswith("mvN_") or k.startswith("mvC_") for k in f)

    # the closed basis absorbs all of it: no unknown-key raise
    phi = S.phi_vector(cls)
    assert len(phi) == 115
    idx = {k: i for i, k in enumerate(S.ESYM_FEATURE_KEYS)}
    assert phi[idx["mover_n_F"]] == 1.0


def test_dphi2_fe_and_wildcard_contribute_nothing() -> None:
    """ΔE_H is untrained for Fe/W: replacing Ni with Fe/W only ever removes terms."""
    cls = _wildcard_fe_class()
    v = S.dphi2(cls)
    assert v.shape == (18,)
    # the Fe mover has no point term (pt_NI / pt_CR are the only point channels)
    assert v[S.H2IDX["pt_NI"]] == 0.0 and v[S.H2IDX["pt_CR"]] == 0.0
    # and no bond term is routed anywhere (an F delta site is skipped outright)
    assert not np.any(v)


def test_wildcard_neighbour_not_miscounted_as_outside() -> None:
    """A W neighbour of an N delta site is skipped, NOT routed into the b*_NU channel.

    This is the trap the explicit skip exists for: without it a W would fall through
    to the U branch (C) or crash sp_key (Python), silently inflating b1_NU/b2_NU.
    """
    d = {(0, 0, 0): "N", (1, 1, 0): "E"}
    with_w = {**d, (1, -1, 0): "W"}
    with_u = {**d, (1, -1, 0): "U"}
    base = S.dphi2_from_maps(dict(d), dict(d), [(0, 0, 0), (1, 1, 0)])
    vw = S.dphi2_from_maps(dict(with_w), dict(with_w), [(0, 0, 0), (1, 1, 0)])
    vu = S.dphi2_from_maps(dict(with_u), dict(with_u), [(0, 0, 0), (1, 1, 0)])
    np.testing.assert_array_equal(vw, base)   # W: no contribution at all
    np.testing.assert_array_equal(vu, base)   # (and the U channel cancels here)
    assert S.H2IDX["b1_NU"] == 14


# ---------------------------------------------------------------------------
# C index layout lockstep (no compiler needed — the C source is parsed)
# ---------------------------------------------------------------------------

_SURR_C = REPO_ROOT / "runtime" / "src" / "core" / "surrogate.c"
_SURR_H = REPO_ROOT / "runtime" / "src" / "core" / "surrogate.h"


def _c_define(src: str, name: str) -> int:
    m = re.search(rf"^#define\s+{name}\s+(-?\d+)\s*$", src, re.M)
    assert m, f"#define {name} not found in the C source"
    return int(m.group(1))


def _c_int_array(src: str, decl: str) -> list[int]:
    m = re.search(rf"{re.escape(decl)}\s*=\s*\{{(.*?)\}};", src, re.S)
    assert m, f"{decl} not found in the C source"
    return [int(x) for x in re.findall(r"-?\d+", m.group(1))]


def test_surrogate_index_layout() -> None:
    """The C phi index helpers reproduce the pinned Python basis, position for position.

    This is the silent-wrong-rate guard: a one-sided reorder of ESYM_FEATURE_KEYS or
    of the C constants compiles clean and reads the wrong feature into every weight.
    Parsed from source (not compiled) so it runs on every machine, unlike
    test_surrogate_parity which needs cc + the machine-local catalogue.
    """
    c_src = _SURR_C.read_text()
    h_src = _SURR_H.read_text()
    idx = {k: i for i, k in enumerate(S.ESYM_FEATURE_KEYS)}
    cats = S.CATEGORIES

    assert _c_define(h_src, "SURR_NPHI") == len(S.ESYM_FEATURE_KEYS)
    assert _c_define(h_src, "SURR_NH2") == len(S.H2FEATS)

    # category codes: the C enum order must be the lex order of the alphabet
    enum_body = re.search(r"enum \{ (CAT_C =.*?) \};", c_src, re.S)
    assert enum_body
    pairs = re.findall(r"CAT_(\w)\s*=\s*(\d+)", enum_body.group(1))
    assert tuple(name for name, _ in pairs) == cats
    assert [int(v) for _, v in pairs] == list(range(len(cats)))

    # scalars
    assert _c_define(c_src, "PHI_ABS_DELTA") == idx["abs_delta_atoms"]
    assert _c_define(c_src, "PHI_DEPTH_PARAM") == idx["depth_param"]
    assert _c_define(c_src, "PHI_DEPTH_SURF") == idx["depth_surface"]
    assert _c_define(c_src, "PHI_MOVER_N_C") == idx["mover_n_C"]
    assert _c_define(c_src, "PHI_MOVER_N_F") == idx["mover_n_F"]
    assert _c_define(c_src, "PHI_N_DELTA") == idx["n_delta"]

    # shells: SHELL_IDX(sh, cat) = base + sh*CAT_COUNT + cat
    m = re.search(r"#define SHELL_IDX\(sh, cat\) \((\d+) \+", c_src)
    assert m
    shell_base = int(m.group(1))
    for sh in range(10):
        for ci, cat in enumerate(cats):
            assert shell_base + sh * len(cats) + ci == idx[f"s{sh}_{cat}"]

    # bonds: BOND_IDX[a][b] over the bondable cats, in category-code order
    bond = _c_int_array(c_src, "static const int BOND_IDX[4][4]")
    bondable = [c for c in cats if c not in S.UNKNOWN_CATS]
    assert len(bond) == 16
    for ai, a in enumerate(bondable):
        for bi, b in enumerate(bondable):
            assert bond[4 * ai + bi] == idx["b_" + "".join(sorted((a, b)))]

    # triangles: 94 + TRI_BASE[lo] + (hi - lo)
    tri_base = _c_int_array(c_src, "static const int TRI_BASE[CAT_COUNT]")
    m = re.search(r"return (\d+) \+ TRI_BASE\[lo\]", c_src)
    assert m
    tri_origin = int(m.group(1))
    for lo_i, lo in enumerate(cats):
        for hi_i in range(lo_i, len(cats)):
            hi = cats[hi_i]
            assert tri_origin + tri_base[lo_i] + (hi_i - lo_i) == idx[f"t3_{lo}{hi}"]

    # mover-neighbour: MV_BASE[mover_cat] + nb_cat
    mv_base = _c_int_array(c_src, "static const int MV_BASE[CAT_COUNT]")
    for mi, mover in enumerate(cats):
        if mover not in S.OCCUPIED_CATS:
            assert mv_base[mi] == -1, f"MV_BASE[{mover}] must be poisoned"
            continue
        for ci, cat in enumerate(cats):
            assert mv_base[mi] + ci == idx[f"mv{mover}_{cat}"]


def test_phi_vector_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """A sym_features key outside the pinned basis raises (loud, never silently dropped)."""
    cls = _synth_class()
    orig = S.sym_features

    def _fake(c: EventClass) -> dict[str, float]:
        d = orig(c)
        d["s99_Z"] = 1.0
        return d

    monkeypatch.setattr(S, "sym_features", _fake)
    with pytest.raises(ValueError, match="not in ESYM_FEATURE_KEYS"):
        S.phi_vector(cls)


# ---------------------------------------------------------------------------
# Ridge + leverage — tiny fixed matrix with hardcoded expected outputs
# ---------------------------------------------------------------------------

_X = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
_Y = np.array([1.0, 2.0, 1.5, 2.5, 3.0])


def test_ridge_fit_std_fixed() -> None:
    """ridge_fit_std reproduces the hand-computed standardized ridge on a 5x2 matrix."""
    mu, sd, ym, w, alpha = S.ridge_fit_std(_X, _Y, 1.0)
    assert alpha == 1.0
    np.testing.assert_allclose(mu, [0.8, 0.6])
    np.testing.assert_allclose(sd, [0.7483314773547883, 0.48989794855663565])
    assert ym == pytest.approx(2.0)
    np.testing.assert_allclose(w, [0.5012938621079772, 0.20346779749806673])


def test_ridge_pred_fixed() -> None:
    """ridge_pred on held-out points matches the hand-computed predictions."""
    m = S.ridge_fit_std(_X, _Y, 1.0)
    pred = S.ridge_pred(m, np.array([[0.5, 0.5], [2.0, 2.0]]))
    np.testing.assert_allclose(pred, [1.757502679528403, 3.385316184351554])


def test_leverage_fixed() -> None:
    """Ainv + z@Ainv@z leverages match the hand-computed values (V5 einsum)."""
    m = S.ridge_fit_std(_X, _Y, 1.0)
    mu, sd, _, _, _ = m
    ainv = S.ridge_ainv(m, _X)
    np.testing.assert_allclose(
        ainv,
        [[0.18006430868167206, -0.04911656693414619],
         [-0.04911656693414619, 0.18006430868167203]],
    )
    lev = S.leverages(_X, mu, sd, ainv)
    np.testing.assert_allclose(
        lev,
        [0.34726688102893893, 0.315112540192926, 0.41157556270096474,
         0.1114683815648446, 0.45444801714898186],
    )


def test_ridge_fit_nointercept_fixed() -> None:
    """The no-intercept ridge (H(σ) ΔΦ fitter) matches the hand-computed theta."""
    theta = S.ridge_fit_nointercept(_X, _Y, 0.5)
    np.testing.assert_allclose(theta, [1.1454545454545455, 1.0181818181818179])


# ---------------------------------------------------------------------------
# EsymModel container + prediction helpers + JSON round-trip
# ---------------------------------------------------------------------------


def _tiny_model() -> S.EsymModel:
    """A small, exactly-round-trippable EsymModel over 3 E_sym + 2 H features."""
    return S.EsymModel(
        model_version="E_sym_v2_ridge_sym2b3b_wf",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        alpha=30.0,
        feature_keys=("a", "b", "c"),
        mu=np.array([0.5, 1.0, 2.0]),
        sd=np.array([1.0, 2.0, 0.5]),
        ym=0.25,
        w=np.array([0.1, -0.2, 0.3]),
        h2_feature_names=("h0", "h1"),
        h2_theta=np.array([1.5, -0.5]),
        ainv=np.array([[2.0, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 1.0]]),
        lev_q75=0.11,
        lev_q90=0.21,
        lev_q95=0.29,
        tier0_nu0_hz=4.17e12,
        context_count_ranges={"N": (63, 128), "C": (1, 11), "E": (83, 174)},
        ea_clamp=(0.0, 2.31),
        conditions="unit-test tiny model",
        n_train=3,
    )


def test_esym_model_json_round_trip(tmp_path: Path) -> None:
    """save_model → load_model reproduces every field exactly (float64 JSON is exact)."""
    m = _tiny_model()
    p = tmp_path / "m.json"
    S.save_model(m, p)
    r = S.load_model(p)
    assert r.model_version == m.model_version
    assert r.dE_model_version == m.dE_model_version
    assert r.alpha == m.alpha
    assert r.feature_keys == m.feature_keys
    assert r.h2_feature_names == m.h2_feature_names
    np.testing.assert_array_equal(r.mu, m.mu)
    np.testing.assert_array_equal(r.sd, m.sd)
    np.testing.assert_array_equal(r.w, m.w)
    np.testing.assert_array_equal(r.h2_theta, m.h2_theta)
    np.testing.assert_array_equal(r.ainv, m.ainv)
    assert r.ym == m.ym
    assert (r.lev_q75, r.lev_q90, r.lev_q95) == (m.lev_q75, m.lev_q90, m.lev_q95)
    assert r.tier0_nu0_hz == m.tier0_nu0_hz
    assert r.context_count_ranges == m.context_count_ranges
    assert r.ea_clamp == m.ea_clamp
    assert r.n_train == m.n_train


def test_prediction_helpers() -> None:
    """predict_esym / predict_dE / leverage / surrogate_barrier match closed-form values."""
    m = _tiny_model()
    phi = [1.5, 3.0, 1.0]  # z = (1.0, 1.0, -2.0)
    # E_sym = z·w + ym = 0.1 - 0.2 - 0.6 + 0.25 = -0.45
    assert S.predict_esym(m, phi) == pytest.approx(-0.45)
    # ΔE = dphi2·theta ; dphi2 = (2, 4) -> 2*1.5 + 4*-0.5 = 1.0
    assert S.predict_dE(m, [2.0, 4.0]) == pytest.approx(1.0)
    # leverage = z·Ainv·z = 2*1 + 0.5*1 + 1*4 = 6.5
    assert S.leverage(m, phi) == pytest.approx(6.5)


def test_json_key_order_deterministic(tmp_path: Path) -> None:
    """The model JSON is written with a deterministic (sorted) key order."""
    m = _tiny_model()
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    S.save_model(m, p1)
    S.save_model(m, p2)
    assert p1.read_text() == p2.read_text()
    import json

    keys = list(json.loads(p1.read_text()).keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Stamping round-trip (pyarrow-guarded)
# ---------------------------------------------------------------------------


def test_stamp_catalogue_parquet_round_trip(tmp_path: Path) -> None:
    """Stamping a mini-catalogue then Parquet round-trip preserves the [C] fields."""
    pytest.importorskip("pyarrow")
    from pylatkmc.ingest.event_class import read_catalogue_parquet, write_catalogue_parquet

    # a small model whose leverage on phi = ||phi||^2 (identity Ainv, zero mu/unit sd)
    n = len(S.ESYM_FEATURE_KEYS)
    model = S.EsymModel(
        model_version="E_sym_v2_ridge_sym2b3b_wf",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        alpha=30.0,
        feature_keys=S.ESYM_FEATURE_KEYS,
        mu=np.zeros(n),
        sd=np.ones(n),
        ym=0.0,
        w=np.zeros(n),
        h2_feature_names=S.H2FEATS,
        h2_theta=np.zeros(len(S.H2FEATS)),
        ainv=np.eye(n),
        lev_q75=50.0,
        lev_q90=80.0,
        lev_q95=100.0,
        tier0_nu0_hz=4.17e12,
        context_count_ranges={"N": (1, 2), "C": (0, 1), "E": (1, 3), "F": (0, 0)},
        ea_clamp=(0.0, 2.0),
        conditions="unit-test",
        n_train=1,
    )

    cls = _synth_class()
    # give the catalogue a second, quarantined class to exercise the tier branch
    cls_q = _synth_class()
    cls_q.class_id = cls.class_id[:-1] + ("0" if cls.class_id[-1] != "0" else "1")
    cls_q.audit_status = "quarantined"
    classes = [cls, cls_q]

    S.stamp_catalogue(classes, model)

    # in-memory checks
    assert len(cls.phi) == 115
    assert cls.model_version == "E_sym_v2_ridge_sym2b3b_wf"
    assert cls.dE_model_version == "H_sigma_v2_surfsplit_aug"
    assert cls.nu0_pair_policy == "harvested_pair"
    lev, hull, mv, tier = cls.fallback_stats
    assert mv == "E_sym_v2_ridge_sym2b3b_wf"
    assert tier == "measured_raw_pair"
    assert isinstance(hull, bool) and lev == pytest.approx(sum(x * x for x in cls.phi))
    assert cls_q.fallback_stats[3] == "quarantined"

    p = tmp_path / "stamped.parquet"
    write_catalogue_parquet(classes, p, metadata={b"pylatkmc.phasec.model": b"unit-test-stamp"})
    back = {c.class_id: c for c in read_catalogue_parquet(p)}

    rc = back[cls.class_id]
    assert tuple(rc.phi) == tuple(cls.phi)
    assert rc.model_version == "E_sym_v2_ridge_sym2b3b_wf"
    assert rc.dE_model_version == "H_sigma_v2_surfsplit_aug"
    assert rc.nu0_pair_policy == "harvested_pair"
    assert rc.fallback_stats[0] == pytest.approx(lev)
    assert rc.fallback_stats[1] is True or rc.fallback_stats[1] is False
    assert rc.fallback_stats[2] == "E_sym_v2_ridge_sym2b3b_wf"
    assert rc.fallback_stats[3] == "measured_raw_pair"
    assert rc.schema_version == CATALOGUE_SCHEMA_VERSION
    assert back[cls_q.class_id].fallback_stats[3] == "quarantined"


# ---------------------------------------------------------------------------
# Production pinned vectors (skips without the machine-local QC'd Parquet)
# ---------------------------------------------------------------------------

# The v1 (68-key) pinned basis order, kept verbatim as the port-fidelity anchor for
# the production vectors below. These four classes are pure NiCr with no WILDCARD
# rows, so the v2 basis must reproduce every one of these 68 values unchanged; the
# 47 new keys are all zero except the two mover-species dummies.
_ESYM_V1_KEYS = (
    "abs_delta_atoms", "b_CC", "b_CE", "b_CN", "b_EE", "b_EN", "b_NN",
    "depth_param", "depth_surface",
    "mvC_C", "mvC_E", "mvC_N", "mvC_U", "mvN_C", "mvN_E", "mvN_N", "mvN_U",
    "n_delta",
    "s0_C", "s0_E", "s0_N", "s0_U", "s1_C", "s1_E", "s1_N", "s1_U",
    "s2_C", "s2_E", "s2_N", "s2_U", "s3_C", "s3_E", "s3_N", "s3_U",
    "s4_C", "s4_E", "s4_N", "s4_U", "s5_C", "s5_E", "s5_N", "s5_U",
    "s6_C", "s6_E", "s6_N", "s6_U", "s7_C", "s7_E", "s7_N", "s7_U",
    "s8_C", "s8_E", "s8_N", "s8_U", "s9_C", "s9_E", "s9_N", "s9_U",
    "t3_CC", "t3_CE", "t3_CN", "t3_CU", "t3_EE", "t3_EN", "t3_EU",
    "t3_NN", "t3_NU", "t3_UU",
)

# class_id -> (phi 68-vector in _ESYM_V1_KEYS order, dphi2 18-vector),
# computed once vs the verbatim 2026-07-21 script.
_PROD_CLEAN_NI = "0257804f0370b043a626d6a19268ca300d999ca2c738327169cd1b842f1c9197"
_PROD_CLEAN_CR = "011d29b208dc43fcca8bc17b944f125d2c11ef0ea7a4aff5059a556b5f7f231f"
_PROD_MULTI_CR = "00821ba9a9a190860f55d0f74f53735de51dacd8c3281ecdcd8bb3dda2463e0e"
_PROD_MULTI_NI = "00fbe757ebeaa250b5dd26affa09885c32d6c2ff54eaf997a488599b3863d9b1"

_PROD_PHI = {
    _PROD_CLEAN_NI: (
        0.0, 0.0, 10.5, 53.5, 381.0, 200.5, 398.5, 7.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.5, 5.0, 6.5,
        0.0, 2.0, 1.0, 5.0, 6.0, 0.0, 0.0, 3.0, 3.0, 0.0, 0.0, 7.0, 17.0, 0.0, 1.0, 5.0, 6.0,
        0.0, 0.0, 11.0, 13.0, 0.0, 1.0, 4.0, 3.0, 0.0, 2.0, 18.0, 20.0, 0.0, 0.0, 2.0, 2.0, 0.0,
        1.0, 10.0, 10.0, 0.0, 0.0, 44.0, 30.0, 0.0, 0.0, 0.5, 1.5, 0.0, 5.0, 9.5, 0.0, 7.5, 0.0,
        0.0,
    ),
    _PROD_CLEAN_CR: (
        0.0, 0.5, 13.0, 22.0, 319.5, 150.0, 337.0, 7.0, 1.0, 0.5, 7.5, 4.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 2.0, 1.0, 5.0, 6.0, 0.0, 1.5, 2.5, 2.0, 0.0, 0.0, 10.0, 14.0, 0.0, 0.0, 4.0, 8.0,
        0.0, 0.0, 10.0, 14.0, 0.0, 0.0, 3.0, 5.0, 0.0, 0.0, 18.0, 22.0, 0.0, 0.0, 2.0, 2.0, 0.0,
        0.0, 14.0, 7.0, 0.0, 0.5, 24.5, 10.0, 39.0, 0.0, 1.0, 1.0, 0.0, 11.5, 6.0, 0.0, 4.5, 0.0,
        0.0,
    ),
    _PROD_MULTI_CR: (
        1.0, 0.0, 9.0, 13.0, 304.5, 134.0, 291.5, 6.0, 1.0, 0.0, 8.0, 4.0, 0.0, 0.0, 1.5, 4.5,
        0.0, 3.0, 0.0, 0.0, 12.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0, 1.0, 14.0, 0.0, 0.5, 2.5, 6.0,
        0.0, 1.0, 1.0, 10.0, 0.0, 0.0, 0.0, 4.0, 0.0, 0.0, 6.5, 9.5, 2.0, 0.0, 0.0, 3.0, 0.0,
        0.0, 5.0, 7.0, 3.0, 0.5, 71.5, 10.0, 52.0, 0.0, 0.0, 0.0, 0.0, 14.0, 10.0, 0.0, 12.0,
        0.0, 0.0,
    ),
    _PROD_MULTI_NI: (
        1.0, 1.0, 8.5, 25.5, 314.5, 296.5, 183.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 12.5, 13.0,
        4.0, 5.0, 1.0, 5.0, 6.0, 0.0, 0.0, 3.0, 3.0, 0.0, 0.0, 15.0, 9.0, 0.0, 0.0, 5.0, 5.0,
        0.0, 1.0, 7.0, 10.0, 0.0, 0.0, 3.0, 2.0, 0.0, 0.0, 20.0, 10.0, 0.0, 0.0, 2.0, 1.0, 0.0,
        1.0, 11.0, 5.0, 2.0, 0.0, 41.5, 17.5, 63.0, 0.0, 0.0, 2.0, 0.0, 13.0, 17.5, 6.5, 15.0,
        2.5, 3.5,
    ),
}

_PROD_DPHI2 = {
    _PROD_CLEAN_NI: (0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                     0.0, 0.0, 0.0),
    _PROD_CLEAN_CR: (0.0, 0.0, -5.0, -1.0, 0.0, 5.0, -3.0, -1.0, -4.0, 0.0, 0.0, 4.0, 0.0, -1.0,
                     0.0, 0.0, 0.0, 0.0),
    _PROD_MULTI_CR: (-1.0, 0.0, -14.0, 0.0, 0.0, 5.0, -4.0, 0.0, -5.0, 0.0, 0.0, 2.0, -2.0, 0.0,
                     0.0, 0.0, -1.0, 1.0),
    _PROD_MULTI_NI: (1.0, 0.0, 14.0, 6.0, 0.0, -6.0, -5.0, 0.0, 5.0, 2.0, 1.0, 3.0, -3.0, -1.0,
                     4.0, 0.0, 3.0, 0.0),
}


@pytest.mark.parametrize("class_id", sorted(_PROD_PHI))
def test_production_pinned_vectors(class_id: str) -> None:
    """Production class_ids reproduce their v1-pinned phi + dphi2 under the v2 basis.

    Rather than re-pinning against the new code (which would pin in any bug it has),
    this asserts the v2 vector *contains* the v1 vector: every one of the 68 v1 keys
    keeps its exact value, the 47 new keys are zero, and the only non-zero addition
    is ``mover_n_C`` (these classes have no Fe, so ``mover_n_F`` is 0). That is the
    port-fidelity guarantee, restated for a superset basis.
    """
    pytest.importorskip("pyarrow")
    if not _QC_PARQUET.exists():
        pytest.skip(f"machine-local QC'd catalogue absent: {_QC_PARQUET}")
    from pylatkmc.ingest.event_class import read_catalogue_parquet

    by_id = {c.class_id: c for c in read_catalogue_parquet(_QC_PARQUET)}
    cls = by_id[class_id]

    v2 = dict(zip(S.ESYM_FEATURE_KEYS, S.phi_vector(cls), strict=True))
    v1 = dict(zip(_ESYM_V1_KEYS, _PROD_PHI[class_id], strict=True))
    assert {k: v2[k] for k in v1} == v1

    expect_cr = 1.0 if class_id in (_PROD_CLEAN_CR, _PROD_MULTI_CR) else 0.0
    assert v2["mover_n_C"] == expect_cr
    assert v2["mover_n_F"] == 0.0
    added = {k: v for k, v in v2.items() if k not in v1 and k not in _V2_EXTRA_KEYS}
    assert set(added.values()) == {0.0}, f"new v2 keys must be 0 here: {added}"

    assert tuple(S.dphi2(cls).tolist()) == _PROD_DPHI2[class_id]
