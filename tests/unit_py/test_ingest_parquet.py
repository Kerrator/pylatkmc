"""EventClass Parquet round-trip + TLV blob decode (Agent A2, contract 11.5 / 9).

Guarded by ``importorskip`` so a bare CI run without the ``[ingest]`` extras
(pyarrow) stays green.
"""

from __future__ import annotations

import hashlib
import math
import struct

import pytest

pytest.importorskip("pyarrow")
pytest.importorskip("pandas")

from pylatkmc.ingest import event_class as ec  # noqa: E402
from pylatkmc.ingest.event_class import (  # noqa: E402
    Coloring,
    DeltaSite,
    DepthKind,
    DepthSig,
    EventClass,
    GateOutcome,
    GateResult,
    Occ,
    OccPredicate,
    PathToken,
    SaddleKind,
    StencilSite,
)


def _class_id(blob: bytes) -> str:
    return hashlib.blake2b(blob, digest_size=32).hexdigest()


def _rich_event() -> EventClass:
    """A fully-populated EventClass exercising nested + nullable fields."""
    cf = (1, 1, 0, 0, 8, ((0, 0, 0, 1, 0), (1, 1, 0, 0, 1)), ((2, 0, 0, 0), (3, 1, 1, 255)),
          ((0, 0, (8, 8)),))
    blob = ec._tlv_encode(cf)
    return EventClass(
        class_id=_class_id(blob),
        canonical_form=cf,
        canonical_blob=blob,
        depth_sig=DepthSig(DepthKind.SURFACE, 8),
        coloring=Coloring.FULL,
        move_shape=0xDEADBEEF,
        family_id=0x0BADF00D,
        delta=(
            DeltaSite((0, 0, 0), Occ.NI, Occ.EMPTY),
            DeltaSite((1, 1, 0), Occ.EMPTY, Occ.NI),
        ),
        delta_atoms=0,
        context=(
            StencilSite((0, 0, 0), OccPredicate("SPECIES", frozenset({Occ.CR}))),
            StencilSite((2, 0, 0), OccPredicate("EMPTY")),
            StencilSite((3, 1, 1), OccPredicate("OUTSIDE")),
        ),
        saddle_token=(PathToken(0, SaddleKind.BRIDGE, (8, 8)),),
        orientation_count=4,
        r_ctx_used=5.0,
        r_id_used=5.0,
        anchor_pred=OccPredicate("SPECIES", frozenset({Occ.CR})),
        t_ref_K=500.0,
        barriers_eV=(0.55, 0.60, 0.65),
        nu0_f_list_hz=(1e13, 1e13, 1e13),
        nu0_b_list_hz=(2e13, float("nan"), 2e13),
        dE_pair_list_eV=(0.1, 0.1),
        k_rate_mean_psinv=1.5e-3,
        Ea_rep_eV=0.57,
        nu0_geo_psinv=10.0,
        Ea_std_eV=0.05,
        n_eff=3.0,
        Ea_mean_eV=0.60,
        Ea_median_eV=0.60,
        backward_class="ab" * 32,
        self_reverse=False,
        dEnergy_eV=0.1,
        pair_status="linked",
        source_rows=(0, 1, 2),
        source_idx_refs=(10, 11, 12),
        source_sim_paths=("/sims/a", "/sims/b"),
        first_seen_cycle=7,
        gate_log=(
            GateResult("G1", GateOutcome.PASS, "in bounds", 0.6),
            GateResult("G2", GateOutcome.NA, "no linked pair", None),
        ),
        audit_status="approved",
    )


def _sparse_event() -> EventClass:
    """A singleton (n<3) EventClass: Ea_std/dEnergy/backward all null; grey."""
    cf = (1, 0, 0, 1, 1, (), (), ())
    blob = ec._tlv_encode(cf)
    return EventClass(
        class_id=_class_id(blob),
        canonical_form=cf,
        canonical_blob=blob,
        depth_sig=DepthSig(DepthKind.SUBSURF, 1),
        coloring=Coloring.GREY,
        move_shape=1,
        family_id=2,
        delta=(),
        delta_atoms=0,
        context=(),
        saddle_token=(),
        orientation_count=1,
        r_ctx_used=4.0,
        r_id_used=4.0,
        anchor_pred=OccPredicate("WILDCARD"),
        t_ref_K=500.0,
        barriers_eV=(0.5,),
        nu0_f_list_hz=(1e13,),
        nu0_b_list_hz=(float("nan"),),
        dE_pair_list_eV=(),
        k_rate_mean_psinv=1.0,
        Ea_rep_eV=0.5,
        nu0_geo_psinv=10.0,
        Ea_std_eV=None,
        n_eff=1.0,
        Ea_mean_eV=0.5,
        Ea_median_eV=0.5,
        backward_class=None,
        dEnergy_eV=None,
        pair_status="unpaired",
        source_rows=(3,),
        source_idx_refs=(13,),
        audit_status="pending",
    )


def test_parquet_round_trip_every_field(tmp_path) -> None:
    """write -> read reproduces every field, including nested + nullable ones."""
    src = _rich_event()
    path = tmp_path / "cat.parquet"
    ec.write_catalogue_parquet([src], path)
    (back,) = ec.read_catalogue_parquet(path)

    assert back.class_id == src.class_id
    assert back.canonical_blob == src.canonical_blob
    assert back.canonical_form == src.canonical_form
    assert back.depth_sig == src.depth_sig
    assert back.coloring == src.coloring
    assert back.move_shape == src.move_shape
    assert back.family_id == src.family_id
    assert back.delta == src.delta
    assert back.context == src.context
    assert back.saddle_token == src.saddle_token
    assert back.orientation_count == src.orientation_count
    assert back.anchor_pred == src.anchor_pred
    assert back.barriers_eV == src.barriers_eV
    assert back.nu0_f_list_hz == src.nu0_f_list_hz
    assert math.isnan(back.nu0_b_list_hz[1])  # NaN preserved in the list
    assert back.dE_pair_list_eV == src.dE_pair_list_eV
    assert back.k_rate_mean_psinv == src.k_rate_mean_psinv
    assert back.Ea_rep_eV == src.Ea_rep_eV
    assert back.nu0_geo_psinv == src.nu0_geo_psinv
    assert back.Ea_std_eV == src.Ea_std_eV
    assert back.backward_class == src.backward_class
    assert back.self_reverse == src.self_reverse
    assert back.dEnergy_eV == src.dEnergy_eV
    assert back.pair_status == src.pair_status
    assert back.source_rows == src.source_rows
    assert back.source_idx_refs == src.source_idx_refs
    assert back.source_sim_paths == src.source_sim_paths
    assert back.first_seen_cycle == src.first_seen_cycle
    assert back.gate_log == src.gate_log
    assert back.audit_status == src.audit_status
    assert back.schema_version == ec.CATALOGUE_SCHEMA_VERSION


def test_parquet_nullables_and_grey(tmp_path) -> None:
    """A singleton grey class round-trips with null Ea_std/dEnergy/backward_class."""
    src = _sparse_event()
    path = tmp_path / "sparse.parquet"
    ec.write_catalogue_parquet([src], path)
    (back,) = ec.read_catalogue_parquet(path)
    assert back.Ea_std_eV is None
    assert back.dEnergy_eV is None
    assert back.backward_class is None
    assert back.coloring == Coloring.GREY
    assert back.pair_status == "unpaired"


def test_parquet_rows_sorted_by_class_id(tmp_path) -> None:
    """Rows are written sorted by class_id regardless of input order (determinism)."""
    rich, sparse = _rich_event(), _sparse_event()
    path = tmp_path / "both.parquet"
    ec.write_catalogue_parquet([rich, sparse], path)  # unsorted input
    back = ec.read_catalogue_parquet(path)
    ids = [b.class_id for b in back]
    assert ids == sorted(ids)


def test_canonical_blob_decodes_back(tmp_path) -> None:
    """canonical_blob round-trips to canonical_form through the stored Parquet blob."""
    src = _rich_event()
    path = tmp_path / "cat.parquet"
    ec.write_catalogue_parquet([src], path)
    (back,) = ec.read_catalogue_parquet(path)
    assert ec.decode_canonical_blob(back.canonical_blob) == src.canonical_form


def test_class_id_is_blake2b_of_blob() -> None:
    """class_id is the 64-hex blake2b-256 of canonical_blob (index-only)."""
    src = _rich_event()
    assert src.class_id == hashlib.blake2b(src.canonical_blob, digest_size=32).hexdigest()
    assert len(src.class_id) == 64


def test_tlv_encoding_byte_exact_golden() -> None:
    """_tlv_encode matches a hand-built TLV golden (contract 7.3 normative)."""
    form = (1, (7,))
    # SEQ(len=2) [ INT(1)  SEQ(len=1)[ INT(7) ] ]
    golden = (
        b"\x02" + struct.pack(">I", 2)
        + b"\x01" + struct.pack(">q", 1)
        + b"\x02" + struct.pack(">I", 1)
        + b"\x01" + struct.pack(">q", 7)
    )
    assert ec._tlv_encode(form) == golden
    assert ec.decode_canonical_blob(golden) == form
    # every int is exactly 9 bytes, every sequence a 5-byte header
    assert len(golden) == 5 + 9 + 5 + 9


def test_arrow_schema_column_order(tmp_path) -> None:
    """The arrow schema preserves the fixed column order on write (schema v4)."""
    import pyarrow.parquet as pq

    path = tmp_path / "cat.parquet"
    ec.write_catalogue_parquet([_rich_event()], path)
    schema = pq.read_schema(path)
    assert schema.names[:3] == ["class_id", "canonical_blob", "schema_version"]
    # schema v2 appends the previously-omitted [C] fields + human-veto reason after
    # gate_log; schema v3 appends the per-member snap residual lists; schema v4 the
    # action axis (action-fingerprint memo 2026-07-30 §7 Phase 1) -- each strictly
    # after the last, so an older reader's column offsets never move.
    tail = schema.names[schema.names.index("gate_log") :]
    assert tail == [
        "gate_log",
        "audit_reason",
        "phi",
        "model_version",
        "dE_model_version",
        "nu0_pair_policy",
        "fallback_stats",
        "mover_max_residual_list",
        "max_residual_list",
        "arrows",
        "action_id",
        "archetype",
        "one_way",
        "action_pair_mismatch",
    ]
    # canonical_form is never a column (reconstructed from canonical_blob).
    assert "canonical_form" not in schema.names
