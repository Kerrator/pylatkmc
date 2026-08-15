"""Phase B tests: EventClass catalogue → oriented patterns → generated tables.

Covers the Phase B contract points (COMPARISON.md §4):

- species-resolved movers (no Ni default anywhere on the v2 path; Cr/Fe
  survive translation with their NAMES, guarding the Occ↔Species enum swap),
- D4h orientation expansion whose transversal size matches Phase A's
  ``orientation_count`` orbit math (and detects the OUTSIDE-broken-symmetry
  case where the matched pattern has MORE symmetry than the decorated class),
- rate baking: ``prefactor_Hz = nu0_geo_psinv × 1e12`` exactly once, chosen
  so the runtime Arrhenius form reproduces ``k_rate_mean`` at ``t_ref_K``,
- counted (never silent) skip policy for empty-delta / non-conserving rows,
- byte-determinism of the emitted C across PYTHONHASHSEED values,
- a cc compile gate for the emitted proclist.c (skips without cc).

Fixtures build ProjectedEvents by hand (the established ``_mk_pe`` pattern
from test_ingest_gate_rcut_mismatch) and run them through the REAL Phase A
``build_class_catalogue`` so the EventClass rows are the genuine article,
not mocks. No pandas/pyarrow needed (Parquet I/O is not exercised here).
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from pylatkmc.ingest import event_class as ec
from pylatkmc.ingest.event_class import (
    Arrow,
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventProjReport,
    GateThresholds,
    Occ,
    OccPredicate,
    PathToken,
    ProjectedEvent,
    SaddleKind,
    StencilSite,
)
from pylatkmc.pattern_codegen import (
    emit_pattern_tables,
    emit_v2_enum,
    emit_v2_rate_table,
    n_procs_of,
)
from pylatkmc.rate_expression import KB_EV_PER_K
from pylatkmc.translator_v2 import (
    HARVESTED_PAIR_POLICY,
    HZ_PER_PSINV,
    to_runtime_frame,
    translate_event_classes,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"

_T_REF = 500.0
_THRESHOLDS = GateThresholds(
    emin_event=0.0,
    emax_event=10.0,
    backward_emin_event=0.0,
    snap_tol=0.9,
    db_tol=0.05,
    rcut=5.0,
)


def _sp_pred(occ: Occ) -> OccPredicate:
    return OccPredicate("SPECIES", frozenset({occ}))


def _mk_pe(**kw: object) -> ProjectedEvent:
    """A minimal Cr 1NN in-plane hop ProjectedEvent; override any field."""
    base: dict[str, object] = dict(
        anchor0=(0, 0, 0),
        delta=(
            DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.CR),
        ),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
        ),
        movers=((0, 0, 0),),
        saddle_tokens=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.CR),),
        depth_sig=DepthSig(DepthKind.BULK_OR_DEEPER, -1),
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
    base.update(kw)
    return ProjectedEvent(**base)  # type: ignore[arg-type]


def _catalogue(events: list[ProjectedEvent]) -> list[ec.EventClass]:
    # Fixtures are stamped measured so the default unstamped gate does not
    # skip them; the gate's own behaviour is locked by
    # test_unstamped_classes_are_skipped_and_counted.
    classes = ec.build_class_catalogue(
        events, t_ref_K=_T_REF, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )
    for c in classes:
        c.nu0_pair_policy = HARVESTED_PAIR_POLICY
    return classes


# ---------------------------------------------------------------------------
# Frame map
# ---------------------------------------------------------------------------


def test_runtime_frame_map_takes_shells_to_runtime_cells() -> None:
    """Crystal 1NN/2NN offsets land on the runtime cells coord_codes.c names."""
    # In-plane 1NN (crystal (1,1,0)) -> (2,0,0) cells = (+nn_d, 0, 0).
    assert to_runtime_frame((1, 1, 0)) == (2, 0, 0)
    # Cross-layer 1NN (1,0,1) -> (1,-1,1) = (nn_d/2, -nn_d/2, +nn_d/sqrt2).
    assert to_runtime_frame((1, 0, 1)) == (1, -1, 1)
    # Axial 2NN (2,0,0) -> (2,-2,0) = the in-plane diagonal 2NN.
    assert to_runtime_frame((2, 0, 0)) == (2, -2, 0)
    # z-axial 2NN unchanged in-plane: (0,0,2) -> (0,0,2).
    assert to_runtime_frame((0, 0, 2)) == (0, 0, 2)
    # Even-parity crystal sites map onto the same-parity sublattice.
    for off in ((1, 1, 0), (2, 0, 0), (2, 1, 1), (0, 0, 2), (3, 1, 0)):
        u, v, w = to_runtime_frame(off)
        assert (u - v) % 2 == 0 and (v - w) % 2 == 0


# ---------------------------------------------------------------------------
# Species-resolved translation
# ---------------------------------------------------------------------------


def test_cr_mover_survives_translation_by_name() -> None:
    """A Cr hop translates with mover species 'Cr' (the enum-swap guard)."""
    patterns, report = translate_event_classes(_catalogue([_mk_pe()]))
    assert report.n_translated == 1
    (pat,) = patterns
    assert pat.mover_species == ("Cr",)
    assert {r.before for r in pat.delta} == {"Cr", "Vacant"}
    assert {r.after for r in pat.delta} == {"Cr", "Vacant"}
    # Anchor = the vacancy end of the hop (rarest predicate).
    assert pat.anchor_species == "Vacant"
    # The anchor row sits at the origin of the re-anchored frame.
    assert any(r.off == (0, 0, 0) and r.before == "Vacant" for r in pat.delta)
    assert report.mover_pattern_counts == {"Cr": 1}


def test_emitted_c_uses_sp_cr_symbol_not_integer() -> None:
    """The emitter writes SP_CR by NAME. Ingest Occ.CR = 2 but runtime
    SP_CR = 3 (SP_FE is 2): emitting integers would silently swap Cr/Fe.

    The negative half is fixture-scoped: THIS catalogue has no stamped Fe class,
    so SP_FE must not appear. Fe emission itself is covered by
    test_fe_mover_emits_sp_fe below — do not read this as "Fe is never emitted".
    """
    patterns, _ = translate_event_classes(_catalogue([_mk_pe()]))
    body = emit_pattern_tables(patterns)
    assert "SP_CR" in body
    assert "SP_FE" not in body  # no Fe anywhere in THIS catalogue


def _mk_fe_pe(**kw: object) -> ProjectedEvent:
    """The Fe twin of ``_mk_pe`` (same geometry, Fe mover)."""
    base: dict[str, object] = dict(
        delta=(
            DeltaSite((0, 0, 0), Occ.FE, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.FE),
        ),
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.FE)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
        ),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.FE),),
    )
    base.update(kw)
    return _mk_pe(**base)


def test_fe_mover_survives_translation_by_name() -> None:
    """An Fe hop translates with mover species 'Fe' (Occ.FE=3 vs SP_FE=2 guard)."""
    patterns, report = translate_event_classes(_catalogue([_mk_fe_pe()]))
    assert report.n_translated == 1
    (pat,) = patterns
    assert pat.mover_species == ("Fe",)
    assert {r.before for r in pat.delta} == {"Fe", "Vacant"}
    assert {r.after for r in pat.delta} == {"Fe", "Vacant"}
    assert report.mover_pattern_counts == {"Fe": 1}


def test_fe_mover_emits_sp_fe() -> None:
    """A STAMPED Fe class DOES reach the emitter as SP_FE (and never as SP_CR).

    Blocker B3's counterpart on the emission side: an Fe class must not be dropped,
    and must not be relabelled Cr. ``nu0_pair_policy`` is the harvested-pair stamp,
    so this also exercises the phase-C raw-pair path rather than the aggregate one.
    """
    classes = _catalogue([_mk_fe_pe()])
    assert all(c.nu0_pair_policy == HARVESTED_PAIR_POLICY for c in classes)
    patterns, report = translate_event_classes(classes, phase_c=True)
    assert report.n_translated == 1 and report.skipped_unstamped == 0
    body = emit_pattern_tables(patterns)
    assert "SP_FE" in body
    assert "SP_CR" not in body


# ---------------------------------------------------------------------------
# Orientation transversal vs Phase A orbit math
# ---------------------------------------------------------------------------


def test_orientation_transversal_matches_phase_a_symmetric() -> None:
    """Context confined to the delta sites: transversal == orientation_count."""
    classes = _catalogue([_mk_pe()])
    patterns, report = translate_event_classes(classes)
    assert report.orientation_mismatches == []
    (pat,) = patterns
    assert len(pat.orientation_ops) == classes[0].orientation_count
    # A single in-plane 1NN hop with no symmetry-breaking context has
    # stabiliser {id, x<->y swap} x {z-sign} -> 16/4 = 4 orientations.
    assert len(pat.orientation_ops) == 4


def test_orientation_transversal_matches_phase_a_broken_symmetry() -> None:
    """A species context row off the hop axis breaks the stabiliser the same
    way for Phase A identity and for the matched pattern."""
    pe = _mk_pe(
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), _sp_pred(Occ.NI)),  # breaks x<->y swap
        ),
    )
    classes = _catalogue([pe])
    patterns, report = translate_event_classes(classes)
    assert report.orientation_mismatches == []
    (pat,) = patterns
    assert len(pat.orientation_ops) == classes[0].orientation_count == 8


def test_outside_rows_drop_and_mismatch_is_reported() -> None:
    """OUTSIDE context is identity-relevant (Phase A) but unmatchable: when
    it alone breaks a symmetry, the matched pattern is MORE symmetric than
    the class and the report must say so (never silently)."""
    pe = _mk_pe(
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((2, 0, 0), OccPredicate("OUTSIDE")),  # unknown at harvest
        ),
    )
    classes = _catalogue([pe])
    patterns, report = translate_event_classes(classes)
    (pat,) = patterns
    # The OUTSIDE row is not emitted as a context row...
    assert len(pat.context) == 0
    # ...so the pattern keeps the 4-orientation transversal while the
    # decorated class counts 8 — recorded, not silent.
    assert len(pat.orientation_ops) == 4
    assert classes[0].orientation_count == 8
    assert len(report.orientation_mismatches) == 1


def test_context_rows_exclude_delta_sites() -> None:
    """Delta rows already pin their sites; context rows must not repeat them."""
    pe = _mk_pe(
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.CR)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
            StencilSite((0, 2, 0), _sp_pred(Occ.NI)),
        ),
    )
    patterns, _ = translate_event_classes(_catalogue([pe]))
    (pat,) = patterns
    delta_offs = {r.off for r in pat.delta}
    assert all(c.off not in delta_offs for c in pat.context)
    assert len(pat.context) == 1  # only the (0,2,0) Ni row survives


# ---------------------------------------------------------------------------
# Rate baking
# ---------------------------------------------------------------------------


def test_rate_baking_reproduces_k_rate_mean_at_t_ref() -> None:
    """prefactor_Hz = nu0_geo_psinv*1e12; Arrhenius at t_ref == k_rate_mean."""
    classes = _catalogue([_mk_pe()])
    patterns, _ = translate_event_classes(classes)
    (pat,) = patterns
    cls = classes[0]
    assert pat.prefactor_Hz == pytest.approx(cls.nu0_geo_psinv * HZ_PER_PSINV)
    assert pat.prefactor_Hz == pytest.approx(1.0e13)  # nu0_fwd was 1e13 Hz
    k_hz = pat.prefactor_Hz * math.exp(-pat.Ea_eV / (KB_EV_PER_K * _T_REF))
    assert k_hz == pytest.approx(cls.k_rate_mean_psinv * HZ_PER_PSINV, rel=1e-9)


# ---------------------------------------------------------------------------
# Skip policy (counted, never silent)
# ---------------------------------------------------------------------------


def test_nonconserving_and_empty_delta_are_skipped_and_counted() -> None:
    vanish = _mk_pe(
        delta=(DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),),
        delta_atoms=-1,
        idx_ref=1,
        source_row=1,
        event_id="vanish",
    )
    noop = _mk_pe(
        delta=(),
        movers=(),
        saddle_tokens=(),
        arrows=(),
        idx_ref=2,
        source_row=2,
        event_id="noop",
    )
    patterns, report = translate_event_classes(_catalogue([_mk_pe(), vanish, noop]))
    assert report.n_classes_in == 3
    assert report.n_translated == 1
    assert report.skipped_nonconserving == 1
    assert report.skipped_empty_delta == 1
    assert len(patterns) == 1


def test_pending_research_classes_are_skipped_and_counted() -> None:
    """A pending_research class (memo 2026-07-22 §3.2) never emits a measured proc."""
    from dataclasses import replace as dc_replace

    from pylatkmc.translator_v2 import PENDING_RESEARCH_POLICY

    classes = _catalogue([_mk_pe()])
    pending = [dc_replace(c, nu0_pair_policy=PENDING_RESEARCH_POLICY) for c in classes]
    patterns, report = translate_event_classes(pending)
    assert patterns == []
    assert report.skipped_pending_research == 1
    assert report.n_translated == 0
    assert "skipped pending-research:  1" in "\n".join(report.summary_lines())


def test_unstamped_classes_are_skipped_and_counted() -> None:
    """An unstamped class (a merge run without a measured set) never bakes
    silently: skipped + counted by default, emitted only via the explicit
    ``include_unstamped=True`` legacy opt-in (2026-08-14 ingest pilot G6)."""
    classes = ec.build_class_catalogue(
        [_mk_pe()], t_ref_K=_T_REF, thresholds=_THRESHOLDS, nu0_fallback_hz=1.0e13
    )
    assert classes[0].nu0_pair_policy is None  # build leaves classes unstamped
    patterns, report = translate_event_classes(classes)
    assert patterns == []
    assert report.skipped_unstamped == 1
    assert report.n_translated == 0
    assert "skipped unstamped:         1" in "\n".join(report.summary_lines())
    patterns, report = translate_event_classes(classes, include_unstamped=True)
    assert report.skipped_unstamped == 0
    assert report.n_translated == 1
    assert len(patterns) == 1


def test_policy_literals_locked_to_ingest_qc() -> None:
    """translator_v2 mirrors the ingest.qc policy literals (no import at module load)."""
    from pylatkmc.ingest.qc import (
        NU0_POLICY_HARVESTED_PAIR,
        NU0_POLICY_PENDING_RESEARCH,
    )
    from pylatkmc.translator_v2 import HARVESTED_PAIR_POLICY, PENDING_RESEARCH_POLICY

    assert NU0_POLICY_HARVESTED_PAIR == HARVESTED_PAIR_POLICY
    assert NU0_POLICY_PENDING_RESEARCH == PENDING_RESEARCH_POLICY


def test_multimover_tokens_bind_by_crystal_rank() -> None:
    """Token[i] belongs to the i-th mover in CRYSTAL-frame lex order (Phase A
    ``start_rank``); the frame map must be applied AFTER that sort — runtime
    offsets do not preserve lex order for every mover pair, and a
    runtime-lex sort mis-binds tokens on concerted (multi-mover) classes."""
    from types import SimpleNamespace

    from pylatkmc.translator_v2 import _movers_in_token_order

    p_off, q_off = (0, 2, 0), (2, 0, 0)  # crystal lex: P < Q
    cls = SimpleNamespace(
        delta=(
            DeltaSite((0, 0, 0), Occ.EMPTY, Occ.NI),
            DeltaSite(p_off, Occ.NI, Occ.CR),
            DeltaSite(q_off, Occ.CR, Occ.EMPTY),
        ),
    )
    expected = [to_runtime_frame(p_off), to_runtime_frame(q_off)]
    assert _movers_in_token_order(cls) == expected  # type: ignore[arg-type]
    # The regression this guards: the runtime images sort the OTHER way
    # ((2,-2,0) < (2,2,0)), so sorting after the map would flip the binding.
    assert expected != sorted(expected)


def test_multimover_transversal_matches_phase_a() -> None:
    """A 2-mover concerted class with DISTINCT saddle tokens translates with
    a transversal that matches Phase A's ``orientation_count`` orbit math
    (end-to-end regression for the crystal-rank token binding)."""
    pe = _mk_pe(
        delta=(
            DeltaSite((0, 0, 0), Occ.EMPTY, Occ.NI),
            DeltaSite((0, 2, 0), Occ.NI, Occ.CR),
            DeltaSite((2, 0, 0), Occ.CR, Occ.EMPTY),
        ),
        context=(
            StencilSite((0, 0, 0), OccPredicate("EMPTY")),
            StencilSite((0, 2, 0), _sp_pred(Occ.NI)),
            StencilSite((2, 0, 0), _sp_pred(Occ.CR)),
        ),
        movers=((0, 2, 0), (2, 0, 0)),
        saddle_tokens=(
            PathToken(0, SaddleKind.BRIDGE, (8, 8)),
            PathToken(1, SaddleKind.BRIDGE, (9, 9)),
        ),
        arrows=(
            Arrow((0, 2, 0), (0, 0, 0), Occ.NI),
            Arrow((2, 0, 0), (0, 2, 0), Occ.CR),
        ),
        event_id="concerted",
        id_saddle="cs",
        id_final="cf",
    )
    patterns, report = translate_event_classes(_catalogue([pe]))
    assert len(patterns) == 1
    assert report.orientation_mismatches == []
    assert patterns[0].mover_species == ("Cr", "Ni")


def test_include_nonconserving_opt_in() -> None:
    vanish = _mk_pe(
        delta=(DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),),
        delta_atoms=-1,
    )
    patterns, report = translate_event_classes(_catalogue([vanish]), include_nonconserving=True)
    assert report.n_translated == 1
    assert report.skipped_nonconserving == 0
    (pat,) = patterns
    # Mover-anchored (no vacancy end to anchor at).
    assert pat.anchor_species == "Cr"


# ---------------------------------------------------------------------------
# Emitted C structure
# ---------------------------------------------------------------------------


def test_emitted_n_procs_is_sum_of_transversals() -> None:
    pe2 = _mk_pe(
        delta=(
            DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI),
        ),
        context=(
            StencilSite((0, 0, 0), _sp_pred(Occ.NI)),
            StencilSite((1, 1, 0), OccPredicate("EMPTY")),
        ),
        arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.NI),),
        idx_ref=1,
        source_row=1,
        event_id="ni-hop",
    )
    patterns, report = translate_event_classes(_catalogue([_mk_pe(), pe2]))
    total = sum(len(p.orientation_ops) for p in patterns)
    assert n_procs_of(patterns) == total == report.n_oriented_patterns
    assert f"enum {{ N_PROCS = {total} }};" in emit_v2_enum(patterns)
    body = emit_v2_rate_table(patterns)
    assert body.count(".prefactor_Hz") == total


def _full_proclist_c(patterns) -> str:
    from pylatkmc.codegen import _PROCLIST_C_PREAMBLE

    pre = _PROCLIST_C_PREAMBLE.format(spec_name="t", temperature_K=500.0, k0_Hz=1e13)
    body = (
        emit_v2_enum(patterns)
        + "\n"
        + emit_v2_rate_table(patterns)
        + "\n"
        + emit_pattern_tables(patterns)
    )
    glue = (
        "\n\nconst int32_t pylatkmc_n_procs = (int32_t)N_PROCS;\n"
        "const RateConst *const pylatkmc_rate_table = rate_table;\n"
        "const ApplyFn   *const pylatkmc_apply_table = apply_table;\n"
    )
    return pre + body + glue


def test_emitted_proclist_compiles(tmp_path: Path) -> None:
    """cc compile gate for the v2 generated C (skips without cc)."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    patterns, _ = translate_event_classes(_catalogue([_mk_pe()]))
    src = tmp_path / "proclist.c"
    src.write_text(_full_proclist_c(patterns))
    res = subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-c",
            str(src),
            "-I",
            str(RUNTIME_CORE),
            "-o",
            str(tmp_path / "proclist.o"),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"generated v2 proclist.c failed to compile:\n{res.stderr}"


def test_emission_deterministic_across_hashseeds(tmp_path: Path) -> None:
    """Full v2 chain (catalogue → translate → emit) is byte-identical across
    PYTHONHASHSEED values — the repo's determinism hard gate."""
    snippet = r"""
import sys
sys.path.insert(0, __TEST_DIR__)
from test_translator_v2 import _catalogue, _full_proclist_c, _mk_pe
from pylatkmc.ingest.event_class import Arrow, DeltaSite, Occ, OccPredicate, StencilSite
from pylatkmc.translator_v2 import translate_event_classes

pe2 = _mk_pe(
    delta=(DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
           DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI)),
    context=(StencilSite((0, 0, 0), OccPredicate("SPECIES", frozenset({Occ.NI}))),
             StencilSite((1, 1, 0), OccPredicate("EMPTY")),
             StencilSite((0, 2, 0), OccPredicate("SPECIES", frozenset({Occ.CR})))),
    arrows=(Arrow((0, 0, 0), (1, 1, 0), Occ.NI),),
    idx_ref=1, source_row=1, event_id="ni-hop",
)
patterns, _ = translate_event_classes(_catalogue([_mk_pe(), pe2]))
sys.stdout.write(_full_proclist_c(patterns))
""".replace("__TEST_DIR__", repr(str(Path(__file__).parent)))
    env_a = {**os.environ, "PYTHONHASHSEED": "1"}
    env_b = {**os.environ, "PYTHONHASHSEED": "424242"}
    r1 = subprocess.run(
        ["python3", "-c", snippet], env=env_a, capture_output=True, text=True, check=True
    )
    r2 = subprocess.run(
        ["python3", "-c", snippet], env=env_b, capture_output=True, text=True, check=True
    )
    assert r1.stdout == r2.stdout, "v2 emission differs across PYTHONHASHSEED"
    assert "N_PROCS" in r1.stdout


# ---------------------------------------------------------------------------
# End-to-end generate() through the spec switch (needs pyarrow for Parquet)
# ---------------------------------------------------------------------------


def test_generate_v2_end_to_end(tmp_path: Path) -> None:
    """A spec with rate_data.event_class_table drives the v2 emission path."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from pylatkmc.codegen import generate
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

    classes = _catalogue([_mk_pe()])
    parquet = tmp_path / "catalogue.parquet"
    ec.write_catalogue_parquet(classes, parquet)

    spec = ModelSpec(
        name="v2_test_model",
        species=["Vacant", "Ni", "Cr"],
        shells=[Shell(name="s1", cutoff_mult=1.05)],
        key=Key(axes=[KeyAxis(name="n_vac_s1", kind="count", max=2, shell="s1", match="vac")]),
        rate_data=RateData(
            event_class_table=parquet,
            temperature_K=500.0,
            k0_Hz=1.0e13,
        ),
    )
    out = tmp_path / "generated"
    written = generate(spec, out)
    assert sorted(p.name for p in written) == ["proclist.c", "proclist.h"]
    src = (out / "proclist.c").read_text()
    assert "V2Pattern" in src and "touchup_a" in src
    assert "SP_CR" in src
    # v2 proclist.h carries the pattern-reach macros for the replica-startup
    # vacuum-gap guard. The 1NN hop re-anchors at the vacancy: one delta row
    # at runtime (-2, 0, 0), context rows all coincide with delta -> (2, 0).
    hdr = (out / "proclist.h").read_text()
    assert "#define PYLATKMC_V2_MAX_REACH_IJ 2" in hdr
    assert "#define PYLATKMC_V2_MAX_REACH_K 0" in hdr
    # Regenerating is byte-stable.
    first = src
    generate(spec, out)
    assert (out / "proclist.c").read_text() == first


def test_generate_v2_rejects_undeclared_species(tmp_path: Path) -> None:
    """A catalogue mover missing from spec.species must fail loudly."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from pylatkmc.codegen import generate
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

    classes = _catalogue([_mk_pe()])  # Cr mover
    parquet = tmp_path / "catalogue.parquet"
    ec.write_catalogue_parquet(classes, parquet)

    spec = ModelSpec(
        name="v2_test_model_ni_only",
        species=["Vacant", "Ni"],  # no Cr
        shells=[Shell(name="s1", cutoff_mult=1.05)],
        key=Key(axes=[KeyAxis(name="n_vac_s1", kind="count", max=2, shell="s1", match="vac")]),
        rate_data=RateData(
            event_class_table=parquet,
            temperature_K=500.0,
            k0_Hz=1.0e13,
        ),
    )
    with pytest.raises(ValueError, match="Cr"):
        generate(spec, tmp_path / "generated")


def test_generate_v2_empty_catalogue_compiles(tmp_path: Path) -> None:
    """An all-skipped catalogue (every class non-conserving) must emit a
    COMPILABLE stub: the empty rate-table branch still has to carry the
    RateConst typedef that the NULL public glue references."""
    pytest.importorskip("pandas")
    pytest.importorskip("pyarrow")
    from pylatkmc.codegen import generate
    from pylatkmc.spec import Key, KeyAxis, ModelSpec, RateData, Shell

    vanish = _mk_pe(
        delta=(DeltaSite((0, 0, 0), Occ.CR, Occ.EMPTY),),
        delta_atoms=-1,
    )
    classes = _catalogue([vanish])
    parquet = tmp_path / "catalogue.parquet"
    ec.write_catalogue_parquet(classes, parquet)
    spec = ModelSpec(
        name="v2_empty_model",
        species=["Vacant", "Ni", "Cr"],
        shells=[Shell(name="s1", cutoff_mult=1.05)],
        key=Key(axes=[KeyAxis(name="n_vac_s1", kind="count", max=2, shell="s1", match="vac")]),
        rate_data=RateData(event_class_table=parquet, temperature_K=500.0, k0_Hz=1.0e13),
    )
    out = tmp_path / "generated"
    generate(spec, out)
    src = (out / "proclist.c").read_text()
    assert "pylatkmc_n_procs = 0" in src
    assert "typedef struct { double prefactor_Hz;" in src  # RateConst emitted
    hdr = (out / "proclist.h").read_text()
    assert "#define PYLATKMC_V2_MAX_REACH_IJ 0" in hdr
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH (emission asserted; compile gate skipped)")
    res = subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-c",
            str(out / "proclist.c"),
            "-I",
            str(RUNTIME_CORE),
            "-o",
            str(tmp_path / "proclist.o"),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"empty-catalogue proclist.c failed to compile:\n{res.stderr}"


def test_pattern_reach_bounds_all_rows() -> None:
    """pattern_reach = max |in-plane| / |k| offset over delta+context rows."""
    from pylatkmc.pattern_codegen import pattern_reach

    patterns, _ = translate_event_classes(_catalogue([_mk_pe()]))
    # Default 1NN in-plane hop, re-anchored at the vacancy: delta rows at
    # (0,0,0) and (-2,0,0); context rows coincide with delta and are dropped.
    assert pattern_reach(patterns) == (2, 0)
    assert pattern_reach([]) == (0, 0)


def test_missing_pyarrow_yields_ingest_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without pyarrow the catalogue loader must point at the [ingest]
    extras. The import inside event_class is lazy (module import succeeds
    without pyarrow), so the failure only surfaces at read time — which is
    why the read call has to live inside the guidance try-block."""
    import builtins
    import sys as _sys

    from pylatkmc.translator_v2 import load_event_class_catalogue

    real_import = builtins.__import__

    def _no_pyarrow(name: str, *args: object, **kwargs: object) -> object:
        if name == "pyarrow" or name.startswith("pyarrow."):
            raise ModuleNotFoundError("No module named 'pyarrow'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    for mod in [m for m in _sys.modules if m == "pyarrow" or m.startswith("pyarrow.")]:
        monkeypatch.delitem(_sys.modules, mod)
    monkeypatch.setattr(builtins, "__import__", _no_pyarrow)
    with pytest.raises(ImportError, match=r"\[ingest\] extras"):
        load_event_class_catalogue("nonexistent.parquet")
