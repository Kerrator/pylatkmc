"""Schema spine for the pylatkmc ingest v2 event-representation layer (Agent A2).

This module is the single source of truth for every shared value type used across
``pylatkmc.ingest`` (enums, predicates, offsets, tokens, projected events, gate
types, and the ``EventClass`` catalogue record), plus the rate-space aggregator
(``aggregate_rate_space``), the ingest gates ``G1``-``G7``, the catalogue
assembler (``build_class_catalogue``) and the Parquet reader/writer.

Determinism (contract Phase A, hard gate)
-----------------------------------------
Nothing here uses ``hash()``, ``set``/``dict`` iteration order, or
``PYTHONHASHSEED``. Identity digests are ``hashlib.blake2b`` over integer TLV
bytes (``canonical_blob``); every reduction iterates a **sorted** member list;
Parquet rows are written sorted by ``class_id``.

Module-load dependency rule (contract 0.2)
------------------------------------------
Module-level intra-package imports are **none**: only stdlib, ``numpy`` and the
core constant ``KB_EV_PER_K`` are imported at load time, so
``import pylatkmc.ingest.event_class`` is cheap and never pulls
``pandas``/``pyarrow``/``ase``. The assembly path (``build_class_catalogue``, the
gates' round-trip) lazily imports ``canonical`` (and, for the executed
orientation, reads the returned ``SymOp`` matrix directly) **inside** the
functions; ``pandas``/``pyarrow`` are imported inside the three Parquet functions
only.

Units (contract 0.4 / project note ``pykmc-k0-units-clock-freeze``)
-------------------------------------------------------------------
Member prefactors ``nu0`` arrive from pyKMC in **Hz**; the on-lattice rate unit
is **ps^-1**. Output rate columns are ps^-1 via ``/ HZ_PER_PSINV`` (= 1e12);
``Ea_rep`` is unit-invariant (the 1e12 cancels).
"""

from __future__ import annotations

import json
import math
import struct
import warnings
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from pylatkmc.rate_expression import KB_EV_PER_K

if TYPE_CHECKING:  # pragma: no cover - typing only, never imported at runtime
    import pyarrow as pa  # type: ignore[import-untyped]


# --------------------------------------------------------------------------- #
# 0.4 Constants (single source of truth)                                      #
# --------------------------------------------------------------------------- #
HZ_PER_PSINV: float = 1.0e12
"""Hz per ps^-1 (1 ps^-1 = 1e12 Hz). Converts pyKMC Hz prefactors to ps^-1."""

A_NOMINAL: float = 3.52
"""Nominal FCC lattice constant (Angstrom)."""

H: float = A_NOMINAL / 2.0
"""Half-lattice spacing h = a/2 (Angstrom)."""

CATALOGUE_SCHEMA_VERSION: int = 3
"""Bump to invalidate the whole Parquet schema deliberately.

v1 -> v2 (2026-07-22, Phase C ingest-QC leg): the formerly-omitted [C] Phase C
rate-model fields (``phi``, ``model_version``, ``dE_model_version``,
``nu0_pair_policy``, ``fallback_stats``) plus the human-veto ``audit_reason`` are
now persisted in the Parquet schema. ``read_catalogue_parquet`` still reads a v1
file (the new columns are absent -> field defaults).

v2 -> v3 (2026-07-29, over-snapping memo §11): per-member snap residuals
(``mover_max_residual_list`` / ``max_residual_list``, Å, aligned with
``barriers_eV``) are persisted so §2-style mover-vs-bystander audits never need a
re-projection. Same read-compat rule: absent columns -> field defaults.
"""

PRIOR_EA_STD_FLOOR_EV: float = 0.02
"""Shrinkage floor for Ea_std (eV); never 0 -> never 'maximally trustworthy'."""


# --------------------------------------------------------------------------- #
# 2.1 Integer code enums                                                      #
# --------------------------------------------------------------------------- #
class Occ(IntEnum):
    """Occupancy integer codes (single source of truth).

    ``OCC_ANY`` (grey-mode collapse) and ``OUTSIDE`` (parity-forbidden /
    out-of-domain / uncovered-by-cluster) are predicate/sentinel codes, never
    stored as a real site occupancy.
    """

    EMPTY = 0
    NI = 1
    CR = 2
    FE = 3
    OCC_ANY = 254
    OUTSIDE = 255


class SaddleKind(IntEnum):
    """Categorical topological class of a saddle (transition-state) site."""

    BRIDGE = 0
    HOLLOW_FCC = 1
    HOLLOW_HCP = 2
    TOP = 3
    OTHER = 4


class DepthKind(IntEnum):
    """Operational depth regime of a mover start site."""

    SURFACE = 0
    SUBSURF = 1
    BULK_OR_DEEPER = 2


class Coloring(IntEnum):
    """Species coloring of the catalogue. GREY collapses occupied species."""

    GREY = 0
    FULL = 1


SYMBOL_TO_OCC: dict[str, Occ] = {"Ni": Occ.NI, "Cr": Occ.CR, "Fe": Occ.FE}
"""Species symbol -> occupancy code. Extend per campaign."""

OCC_TO_SYMBOL: dict[Occ, str] = {Occ.NI: "Ni", Occ.CR: "Cr", Occ.FE: "Fe"}
"""Occupancy code -> species symbol (occupied species only)."""


def type_to_occ(symbol: str) -> Occ:
    """Map a pyKMC species symbol to its occupancy code.

    Raises ``KeyError`` on an unknown symbol (deterministic, explicit).
    """
    return SYMBOL_TO_OCC[symbol]


def occ_to_symbol(o: Occ) -> str:
    """Map an occupied occupancy code to its species symbol.

    Raises ``KeyError`` for EMPTY / OCC_ANY / OUTSIDE (not real species).
    """
    return OCC_TO_SYMBOL[o]


# --------------------------------------------------------------------------- #
# 2.2 Value types                                                             #
# --------------------------------------------------------------------------- #
Offset = tuple[int, int, int]
"""Integer FCC lattice offset (i, j, k), even-parity."""

_PredKind = Literal["SPECIES", "EMPTY", "OCC_ANY", "WILDCARD", "OUTSIDE"]


@dataclass(frozen=True)
class OccPredicate:
    """A per-site occupancy predicate used in the identity context (contract 2.2)."""

    kind: _PredKind
    species: frozenset[Occ] = frozenset()

    def code(self, coloring: Coloring) -> int:
        """Integer used in the canonical key (contract 7.3).

        ``EMPTY -> 0``, ``OUTSIDE -> 255``, ``WILDCARD -> 253``,
        ``OCC_ANY -> 254``; ``SPECIES`` is the single species int in FULL colour,
        collapsed to ``254`` in GREY.
        """
        if self.kind == "EMPTY":
            return int(Occ.EMPTY)
        if self.kind == "OUTSIDE":
            return int(Occ.OUTSIDE)
        if self.kind == "WILDCARD":
            return 253
        if self.kind == "OCC_ANY":
            return int(Occ.OCC_ANY)
        if self.kind == "SPECIES":
            if coloring == Coloring.GREY:
                return int(Occ.OCC_ANY)
            if not self.species:
                raise ValueError("SPECIES predicate with empty species set")
            return int(min(self.species))
        raise ValueError(f"unknown OccPredicate kind: {self.kind!r}")


@dataclass(frozen=True)
class StencilSite:
    """One decorated context site: an integer offset + its occupancy predicate."""

    off: Offset
    pred: OccPredicate


@dataclass(frozen=True)
class DeltaSite:
    """One occupancy change: an integer offset with before/after occupancy."""

    off: Offset
    before: Occ
    after: Occ


@dataclass(frozen=True)
class PathToken:
    """Per-mover categorical saddle mechanism label (contract 3.3)."""

    start_rank: int
    kind: SaddleKind
    coord_sig: tuple[int, ...]


@dataclass(frozen=True)
class DepthSig:
    """Operational depth signature (contract 4.1)."""

    kind: DepthKind
    param: int


# --------------------------------------------------------------------------- #
# 4.1 Per-event projection report (carried on ProjectedEvent)                 #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EventProjReport:
    """Per-event snap residual / diameter / mover-agreement detail (contract 4.1).

    Defined here (not in ``projection.py``) so that it is reachable through the
    module-load DAG: ``event_class`` imports nothing intra-package, while
    ``event_projection`` (which builds ``ProjectedEvent``) and ``projection`` both
    import ``event_class``. The gates read its attributes directly.

    ``frame_unfit_reason`` is non-``None`` when the robust frame fit found no FCC
    frame for the cluster (memo 2026-07-22 s3.6): the event carries no lattice
    representation (empty delta/context/movers, infinite residuals) and gate G3
    FAILs it as ``FRAME_UNFIT`` before any snap-residual is evaluated.
    """

    max_residual: float
    mover_max_residual: float
    diameter: float
    mover_agreement: bool
    frame_unfit_reason: str | None = None


# --------------------------------------------------------------------------- #
# 2.3 ProjectedEvent (output of A4, input to A2 assembly + A5 identity)       #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ProjectedEvent:
    """One pyKMC reference row projected onto the FCC frame (contract 2.3)."""

    anchor0: Offset
    delta: tuple[DeltaSite, ...]
    delta_atoms: int
    context: tuple[StencilSite, ...]
    movers: tuple[Offset, ...]
    saddle_tokens: tuple[PathToken, ...]
    depth_sig: DepthSig
    coloring: Coloring
    r_ctx_used: float
    truncated: bool
    # --- rate/pairing raw data (per this row) ---
    Ea_fwd_eV: float
    nu0_fwd_hz: float
    k_row: float
    id_saddle: str
    id_final: str
    event_id: str
    idx_ref: int
    idx_backward: int
    move_atom_idx: int
    source_row: int
    # --- gate provenance ---
    proj_report: EventProjReport


# --------------------------------------------------------------------------- #
# 2.4 Gate types                                                              #
# --------------------------------------------------------------------------- #
class GateOutcome(IntEnum):
    """Gate outcome codes."""

    PASS = 0
    FAIL = 1
    WARN = 2
    NA = 3


# Severity ranking used to aggregate a gate outcome over a class's members:
# FAIL dominates, then WARN, then a definite PASS, then NA (not applicable).
_OUTCOME_SEVERITY: dict[GateOutcome, int] = {
    GateOutcome.NA: 0,
    GateOutcome.PASS: 1,
    GateOutcome.WARN: 2,
    GateOutcome.FAIL: 3,
}


@dataclass(frozen=True)
class GateResult:
    """One gate's verdict for the audit record (contract 2.4)."""

    gate: str
    outcome: GateOutcome
    detail: str
    value: float | None = None


@dataclass(frozen=True)
class GateThresholds:
    """Thresholds for the ingest gates (contract 8).

    ``mover_snap_tol`` keys the mover-keyed G3 (memo 2026-07-29 §4): an event is
    truly off-lattice iff any *mover's* snap residual reaches it (or the frame is
    unfit). ``bystander_mask_tol`` keys the §6 context masking: a *static*
    bystander whose residual reaches it has its context row demoted to
    ``WILDCARD`` before canonicalisation. The two share the 0.5 Å default (one
    measured valley, two named uses).

    ``snap_tol`` is RETIRED as a gate input (memo 2026-07-29 §4): no gate reads
    it any more. It is kept one release for CLI compatibility and as a historical
    conditions-stamp parameter — old catalogues stay interpretable via their
    stamps (memo §7).
    """

    emin_event: float
    emax_event: float
    backward_emin_event: float
    snap_tol: float = 0.9
    db_tol: float = 0.05
    rcut: float = 5.0
    mover_snap_tol: float = 0.5
    bystander_mask_tol: float = 0.5


# --------------------------------------------------------------------------- #
# 2.5 EventClass — the catalogue record                                       #
# --------------------------------------------------------------------------- #
@dataclass
class EventClass:
    """The persisted catalogue record, keyed by ``class_id`` (contract 2.5).

    Phase A populates every ``[A]`` field. The ``[C]`` Phase C rate-model fields
    (``phi``, ``model_version``, ``dE_model_version``, ``nu0_pair_policy``,
    ``fallback_stats``) and the human-veto ``audit_reason`` stay at their empty
    defaults until Phase C, but are **persisted** in the (schema-v2) Parquet schema
    so an ingest-QC re-emission can stamp them. Treat as write-once during
    assembly; the ingest-QC pass (``pylatkmc.ingest.qc``) is the only other writer,
    and it only sets ``audit_status``/``audit_reason``/``schema_version``.
    """

    # --- identity ---
    class_id: str
    canonical_form: tuple[Any, ...]
    canonical_blob: bytes
    depth_sig: DepthSig
    coloring: Coloring
    move_shape: int
    family_id: int
    delta: tuple[DeltaSite, ...]
    delta_atoms: int
    context: tuple[StencilSite, ...]
    saddle_token: tuple[PathToken, ...]
    orientation_count: int
    r_ctx_used: float
    r_id_used: float
    anchor_pred: OccPredicate
    # --- rate (evaluated at t_ref_K) ---
    t_ref_K: float
    barriers_eV: tuple[float, ...]
    nu0_f_list_hz: tuple[float, ...]
    nu0_b_list_hz: tuple[float, ...]
    dE_pair_list_eV: tuple[float, ...]
    k_rate_mean_psinv: float
    Ea_rep_eV: float
    nu0_geo_psinv: float
    Ea_std_eV: float | None
    n_eff: float
    Ea_mean_eV: float
    Ea_median_eV: float
    # --- per-member snap residuals (Å, aligned with barriers_eV; schema v3,
    #     memo 2026-07-29 §11 — §2-style audits without re-projection) ---
    mover_max_residual_list: tuple[float, ...] = ()
    max_residual_list: tuple[float, ...] = ()
    # --- Phase C rate-model fields [C] (empty until Phase C populates them) ---
    phi: tuple[float, ...] = ()
    model_version: str | None = None
    dE_model_version: str | None = None
    nu0_pair_policy: str | None = None
    # --- pairing ---
    backward_class: str | None = None
    self_reverse: bool = False
    dEnergy_eV: float | None = None
    pair_status: Literal["linked", "synthesized_balanced", "self", "unpaired"] = "unpaired"
    # --- provenance / curation ---
    source_rows: tuple[int, ...] = ()
    source_idx_refs: tuple[int, ...] = ()
    source_sim_paths: tuple[str, ...] = ()
    first_seen_cycle: int = 0
    gate_log: tuple[GateResult, ...] = ()
    audit_status: Literal["approved", "pending", "rejected", "quarantined"] = "pending"
    audit_reason: str = ""
    fallback_stats: tuple[Any, ...] = ()
    schema_version: int = CATALOGUE_SCHEMA_VERSION


# --------------------------------------------------------------------------- #
# 2.6 Rate-space aggregation (contract 6.1)                                   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RateAgg:
    """Result of rate-space aggregation of one class's repeated measurements."""

    k_rate_mean_psinv: float
    Ea_rep_eV: float
    nu0_geo_psinv: float
    Ea_std_eV: float | None
    n_eff: float
    Ea_mean_eV: float
    Ea_median_eV: float
    n_members: int


def _resolve_nu0(nu0: float, fallback_hz: float) -> float:
    """A member nu0 in Hz, replaced by ``fallback_hz`` when NaN or non-positive."""
    if math.isfinite(nu0) and nu0 > 0.0:
        return nu0
    return fallback_hz


def aggregate_rate_space(
    barriers_eV: Sequence[float],
    nu0_list_hz: Sequence[float],
    t_ref_K: float,
    *,
    nu0_fallback_hz: float,
    prior_ea_std_floor_eV: float = PRIOR_EA_STD_FLOOR_EV,
) -> RateAgg:
    """Rate-space aggregation of repeated measurements of ONE physical class.

    Members are paired ``(Ea_i, nu0_i)`` and **sorted** by ``(Ea_eV, nu0_hz)``
    before any summation, for bit-reproducibility. Missing ``nu0_i`` (NaN / <= 0)
    falls back to ``nu0_fallback_hz``. The executed rate is the occurrence-weighted
    mean of member rates, converted to ps^-1::

        k_i               = nu0_i[Hz] * exp(-Ea_i / (kB * T))       # s^-1
        k_rate_mean_psinv = mean_i(k_i) / HZ_PER_PSINV
        nu0_geo_psinv     = geomean_i(nu0_i[Hz]) / HZ_PER_PSINV
        Ea_rep_eV         = -kB*T * ln(k_rate_mean_psinv / nu0_geo_psinv)

    Never ``exp(-mean(Ea))`` (Jensen error). ``Ea_std_eV`` is ``None`` for n < 3;
    for n >= 3 it is ``sqrt(max(sample_var, prior_ea_std_floor_eV**2))`` (never 0).
    ``n_eff = n_members`` in Phase A. By construction the single-Arrhenius form
    ``nu0_geo * exp(-Ea_rep / kBT)`` reproduces ``k_rate_mean`` exactly at
    ``t_ref_K``.
    """
    if len(barriers_eV) != len(nu0_list_hz):
        raise ValueError(
            f"barriers ({len(barriers_eV)}) and nu0 ({len(nu0_list_hz)}) length mismatch"
        )
    n = len(barriers_eV)
    if n == 0:
        nan = float("nan")
        return RateAgg(nan, nan, nan, None, 0.0, nan, nan, 0)

    kT = KB_EV_PER_K * t_ref_K
    resolved = [
        (float(ea), _resolve_nu0(float(nu0), nu0_fallback_hz))
        for ea, nu0 in zip(barriers_eV, nu0_list_hz, strict=True)
    ]
    # SORT before any reduction (deterministic, order-independent).
    resolved.sort(key=lambda p: (p[0], p[1]))
    ea_sorted = np.array([p[0] for p in resolved], dtype=np.float64)
    nu0_sorted = np.array([p[1] for p in resolved], dtype=np.float64)

    k_i = nu0_sorted * np.exp(-ea_sorted / kT)
    k_rate_mean_psinv = float(np.mean(k_i)) / HZ_PER_PSINV
    nu0_geo_hz = float(np.exp(np.mean(np.log(nu0_sorted))))
    nu0_geo_psinv = nu0_geo_hz / HZ_PER_PSINV
    ea_rep = -kT * math.log(k_rate_mean_psinv / nu0_geo_psinv)

    ea_std: float | None
    if n < 3:
        ea_std = None
    else:
        sample_var = float(np.var(ea_sorted, ddof=1))
        ea_std = math.sqrt(max(sample_var, prior_ea_std_floor_eV**2))

    return RateAgg(
        k_rate_mean_psinv=k_rate_mean_psinv,
        Ea_rep_eV=ea_rep,
        nu0_geo_psinv=nu0_geo_psinv,
        Ea_std_eV=ea_std,
        n_eff=float(n),
        Ea_mean_eV=float(np.mean(ea_sorted)),
        Ea_median_eV=float(np.median(ea_sorted)),
        n_members=n,
    )


# --------------------------------------------------------------------------- #
# TLV byte encoding (contract 7.3) — inverse decoder for Parquet reconstruction #
# --------------------------------------------------------------------------- #
_INT_TAG = b"\x01"
_SEQ_TAG = b"\x02"


def _tlv_encode(obj: Any) -> bytes:
    """Self-delimiting tag-length-value encoding of a nested int/tuple form.

    Mirrors the normative ``canonical_blob`` encoding (contract 7.3):
    ``INT_TAG + pack('>q', v)`` for ints, ``SEQ_TAG + pack('>I', n) + children``
    for sequences. ``canonical.py`` owns the forward encoder for identity; this
    copy exists so ``event_class`` can build/verify blobs and decode them back.
    """
    if isinstance(obj, bool):
        return _INT_TAG + struct.pack(">q", int(obj))
    if isinstance(obj, int):
        return _INT_TAG + struct.pack(">q", int(obj))
    if isinstance(obj, (tuple, list)):
        head = _SEQ_TAG + struct.pack(">I", len(obj))
        return head + b"".join(_tlv_encode(e) for e in obj)
    raise TypeError(f"canonical_form may only hold ints and tuples, got {type(obj)!r}")


def _tlv_decode_at(blob: bytes, pos: int) -> tuple[Any, int]:
    tag = blob[pos : pos + 1]
    if tag == _INT_TAG:
        (v,) = struct.unpack(">q", blob[pos + 1 : pos + 9])
        return v, pos + 9
    if tag == _SEQ_TAG:
        (count,) = struct.unpack(">I", blob[pos + 1 : pos + 5])
        pos += 5
        items: list[Any] = []
        for _ in range(count):
            val, pos = _tlv_decode_at(blob, pos)
            items.append(val)
        return tuple(items), pos
    raise ValueError(f"bad TLV tag {tag!r} at offset {pos}")


def decode_canonical_blob(blob: bytes) -> tuple[Any, ...]:
    """Inverse of the contract-7.3 TLV encoding: bytes -> ``canonical_form``."""
    value, pos = _tlv_decode_at(blob, 0)
    if pos != len(blob):
        raise ValueError(f"trailing bytes after TLV decode ({pos} != {len(blob)})")
    if not isinstance(value, tuple):
        raise ValueError("canonical_blob top level is not a sequence")
    return value


# --------------------------------------------------------------------------- #
# 2.7 / 8 Gates G1-G7                                                         #
# --------------------------------------------------------------------------- #
def gate_g1_barrier_bounds(
    pe: ProjectedEvent,
    emin_event: float,
    emax_event: float,
    backward_emin_event: float,
) -> GateResult:
    """G1: forward barrier bounds ``emin_event <= Ea_fwd <= emax_event``.

    Each ingested row's own barrier is bounds-checked; the backward-leg floor
    (``backward_emin_event``, contract 8) applies when that leg is itself
    ingested. FAIL when out of bounds.
    """
    ea = pe.Ea_fwd_eV
    if not math.isfinite(ea):
        return GateResult("G1", GateOutcome.FAIL, f"OUTLIER_BARRIER: Ea_fwd={ea}", ea)
    if ea < emin_event:
        return GateResult(
            "G1",
            GateOutcome.FAIL,
            f"OUTLIER_BARRIER: Ea_fwd={ea:.4f} < emin_event={emin_event:.4f}",
            ea,
        )
    if ea > emax_event:
        return GateResult(
            "G1",
            GateOutcome.FAIL,
            f"OUTLIER_BARRIER: Ea_fwd={ea:.4f} > emax_event={emax_event:.4f}",
            ea,
        )
    return GateResult(
        "G1",
        GateOutcome.PASS,
        f"Ea_fwd={ea:.4f} in [{emin_event:.4f}, {emax_event:.4f}]",
        ea,
    )


def gate_g2_detailed_balance(
    fwd: ProjectedEvent,
    bwd: ProjectedEvent | None,
    t_ref_K: float,
    db_tol: float = 0.05,
) -> GateResult:
    """G2: real detailed balance on a linked forward/backward pair (contract 8).

    ``NA`` when there is no linked backward partner. Otherwise checks the
    independent relation, in ln-rate units::

        residual = | ln(k_f/k_b) - (ln(nu0_f/nu0_b) - dE_pair/kT) |

    where ``k_f``/``k_b`` are pyKMC's stored per-row ``k`` (the independent
    channel) and ``dE_pair = Ea_fwd - Ea_bwd``. FAIL when ``residual >= db_tol``.
    The ratio form is unit-invariant (avoids the Hz vs ps^-1 clock-freeze trap),
    so this is a genuine failable test, not a tautology.
    """
    if bwd is None:
        return GateResult("G2", GateOutcome.NA, "no linked backward pair", None)

    kf, kb = fwd.k_row, bwd.k_row
    nu0_f, nu0_b = fwd.nu0_fwd_hz, bwd.nu0_fwd_hz
    if not (math.isfinite(kf) and kf > 0 and math.isfinite(kb) and kb > 0):
        return GateResult("G2", GateOutcome.NA, "stored k unavailable/non-positive", None)
    if not (math.isfinite(nu0_f) and nu0_f > 0 and math.isfinite(nu0_b) and nu0_b > 0):
        return GateResult("G2", GateOutcome.NA, "nu0 unavailable/non-positive", None)

    kT = KB_EV_PER_K * t_ref_K
    dE_pair = fwd.Ea_fwd_eV - bwd.Ea_fwd_eV
    lhs = math.log(kf / kb)
    rhs = math.log(nu0_f / nu0_b) - dE_pair / kT
    residual = abs(lhs - rhs)
    if residual < db_tol:
        return GateResult(
            "G2", GateOutcome.PASS, f"detailed-balance residual={residual:.4f} < {db_tol}", residual
        )
    return GateResult(
        "G2",
        GateOutcome.FAIL,
        f"PAIR_CLOSURE: detailed-balance residual={residual:.4f} >= {db_tol}",
        residual,
    )


def gate_g2_pair_spread(
    dE_pair_list: Sequence[float],
    ratio_terms: Sequence[tuple[float, float, float, float]],
    t_ref_K: float,
    db_tol: float = 0.05,
) -> GateResult:
    """G2 (class-level): the real detailed-balance / fold-in check (contract 8, C2).

    The per-pair :func:`gate_g2_detailed_balance` can only test one row's stored ``k``
    for self-consistency; because pyKMC stores ``k = nu0*exp(-Ea/kT)``, its ratio
    residual is identically zero for any pyKMC-consistent pair and so cannot detect a
    fold-in. This class-level gate adds the two conditions the single-pair form cannot
    express, evaluated over a class's linked forward/backward members:

    1. **Per-member ``dE_pair`` spread** ``max - min < db_tol``. A genuine class is a
       set of repeated measurements of one reversible process, so every member's
       ``dE_pair = Ea_fwd - Ea_bwd`` agrees; a *fold-in* of two distinct processes into
       one class shows up as a spread far above ``db_tol`` (the C2/C4 fold-in detector).
    2. **Independent-mean detailed balance** -- the residual
       ``|ln(k_f/k_b) - (ln(nu0_f/nu0_b) - <dE_pair>/kT)| < db_tol`` for every linked
       member, using the class-mean ``<dE_pair>`` (the independent channel, contract
       8's ``dEnergy``) instead of the member's own ``dE_pair`` (which would cancel to
       0). A member whose stored ``k`` implies a ``dE_pair`` off the class mean fails.

    Returns ``NA`` with fewer than two linked pairs (no spread and no independent mean
    exist; the per-pair gate covers stored-``k`` consistency in that case). ``db_tol``
    doubles as the eV spread threshold and the ln-rate residual threshold (contract 8).
    """
    finite = [float(d) for d in dE_pair_list if math.isfinite(d)]
    if len(finite) < 2:
        return GateResult("G2", GateOutcome.NA, "fewer than 2 linked pairs (no class spread)", None)

    spread = max(finite) - min(finite)
    if spread >= db_tol:
        return GateResult(
            "G2",
            GateOutcome.FAIL,
            f"PAIR_CLOSURE: dE_pair spread={spread:.4f} >= db_tol={db_tol} (fold-in)",
            spread,
        )

    kT = KB_EV_PER_K * t_ref_K
    mean_dE = math.fsum(finite) / len(finite)
    max_resid = 0.0
    for kf, kb, nu0_f, nu0_b in ratio_terms:
        if not (
            math.isfinite(kf)
            and kf > 0.0
            and math.isfinite(kb)
            and kb > 0.0
            and math.isfinite(nu0_f)
            and nu0_f > 0.0
            and math.isfinite(nu0_b)
            and nu0_b > 0.0
        ):
            continue
        resid = abs(math.log(kf / kb) - (math.log(nu0_f / nu0_b) - mean_dE / kT))
        max_resid = max(max_resid, resid)
    if max_resid >= db_tol:
        return GateResult(
            "G2",
            GateOutcome.FAIL,
            f"PAIR_CLOSURE: detailed-balance residual={max_resid:.4f} >= db_tol={db_tol}",
            max_resid,
        )
    return GateResult(
        "G2",
        GateOutcome.PASS,
        f"dE_pair spread={spread:.4f} < db_tol; db residual={max_resid:.4f}",
        spread,
    )


def gate_g3_snap_residual(pe: ProjectedEvent, mover_snap_tol: float = 0.5) -> GateResult:
    """G3: mover-keyed off-lattice gate (memo 2026-07-29 §4).

    ``FAIL iff frame_unfit OR mover_max_residual >= mover_snap_tol``. An event is
    truly off-lattice only when an atom that *changes site* cannot be trusted on
    the lattice; a static bystander's relaxation (surface sag) no longer FAILs —
    its context row is masked to ``WILDCARD`` instead (§6, in ``project_event``).
    FAIL is enforced as a build-time drop into the discard ledger (§5,
    ``reftable``), so a FAILing event never joins a class; the aggregated
    class-level G3 must therefore always PASS — a class-level FAIL is a pipeline
    bug, not data.

    Both residuals are recorded in the detail (audit): ``mover_max_residual``
    decides, ``max_residual`` contextualises.

    A frame-unfit event (no orthogonal-axis FCC frame exists; memo 2026-07-22 s3.6)
    FAILs here **before** any snap residual is evaluated -- the ``FRAME_UNFIT``
    detail carries the fitter's reason so the audit trail records why the event has
    no lattice representation.
    """
    rep = pe.proj_report
    if rep.frame_unfit_reason is not None:
        return GateResult(
            "G3",
            GateOutcome.FAIL,
            f"FRAME_UNFIT: {rep.frame_unfit_reason}",
            None,
        )
    if rep.mover_max_residual >= mover_snap_tol:
        return GateResult(
            "G3",
            GateOutcome.FAIL,
            f"MOVER_OFFLATTICE: mover_max_residual={rep.mover_max_residual:.3f} >= "
            f"mover_snap_tol={mover_snap_tol} (max_residual={rep.max_residual:.3f})",
            rep.mover_max_residual,
        )
    return GateResult(
        "G3",
        GateOutcome.PASS,
        f"mover_max_residual={rep.mover_max_residual:.3f} < {mover_snap_tol} "
        f"(max_residual={rep.max_residual:.3f})",
        rep.mover_max_residual,
    )


def gate_g4_round_trip(pe: ProjectedEvent) -> GateResult:
    """G4: mover agreement, plus the ideal-site re-projection round-trip (contract 8).

    The mover-agreement half (``move_atom_idx in detected movers``) is a genuine,
    failable check taken from the projection report; it catches the concerted-mover
    mislabel and FAILs when it does not hold.

    The contract's other half -- re-expand the projected event to ideal positions,
    re-``project_event`` it, and require an identical ``class_id`` -- needs a
    re-projection-from-ideal-sites entry point that the section-5 event-projection
    API does not expose in Phase A. A same-object ``class_id(pe) == class_id(pe)``
    comparison is *vacuous* (deterministic canonicalisation makes it always equal, so
    it can never catch a mis-projection); reporting that as ``PASS`` would falsely
    claim the round-trip is satisfied. Instead the round-trip half is reported
    **NA** (deferred, contract 13 deviation): mover agreement holds but the round-trip
    is not verifiable here. ``class_id`` is still evaluated once as a canonicalisation
    smoke test; a failed or malformed canonicalisation is surfaced as WARN.
    """
    if not pe.proj_report.mover_agreement:
        return GateResult(
            "G4", GateOutcome.FAIL, "MOVER_MISMATCH: move_atom_idx not in detected movers", None
        )
    try:
        from pylatkmc.ingest import canonical

        cid = canonical.class_id(pe)
    except Exception as exc:  # noqa: BLE001 - canonicalisation failed -> flag for audit
        return GateResult("G4", GateOutcome.WARN, f"could not canonicalise: {exc}", None)
    if not (isinstance(cid, str) and len(cid) == 64):
        return GateResult("G4", GateOutcome.WARN, f"canonical id malformed: {cid!r}", None)
    return GateResult(
        "G4",
        GateOutcome.NA,
        "mover agreement ok; ideal-site re-projection round-trip deferred (contract 13)",
        None,
    )


def gate_g5_conservation(pe: ProjectedEvent) -> GateResult:
    """G5: atom-conserving events (before/after species multiset equal).

    Compares the multiset of ``before`` occupancies against ``after`` over the
    delta sites and requires ``delta_atoms == 0``. FAIL surfaces non-conservative
    events (dissolution flips this later).
    """
    before = sorted(int(ds.before) for ds in pe.delta)
    after = sorted(int(ds.after) for ds in pe.delta)
    if before == after and pe.delta_atoms == 0:
        return GateResult("G5", GateOutcome.PASS, "species multiset conserved", 0.0)
    return GateResult(
        "G5",
        GateOutcome.FAIL,
        f"non-conservative: delta_atoms={pe.delta_atoms}, before={before}, after={after}",
        float(pe.delta_atoms),
    )


def gate_g6_context_completeness(pe: ProjectedEvent) -> GateResult:
    """G6: cluster covers the full r_ctx footprint of every moved site.

    WARN (not FAIL) when ``pe.truncated``: the class is admitted but flagged for a
    larger-``rcut`` re-harvest.
    """
    if pe.truncated:
        return GateResult(
            "G6", GateOutcome.WARN, "TRUNCATED: cluster did not cover full r_ctx footprint", None
        )
    return GateResult("G6", GateOutcome.PASS, "full r_ctx context covered", None)


def gate_g7_cluster_integrity(pe: ProjectedEvent, rcut: float) -> GateResult:
    """G7: min-image-unwrapped cluster diameter ``< 2*rcut`` (contract 8).

    FAIL routes to audit as a straddling / collision cluster. The FAIL detail also
    carries an actionable ``rcut`` hint, because the #1 way this gate fails in the
    wild is a *configuration* mismatch, not bad data: on 2026-07-17 the first real
    ingest of ``production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle`` FAILed
    G7 on 445/445 rows because ``GateThresholds.rcut`` defaulted to 5.0 A while the
    pyKMC run used rcut ~= 8 A. Reference clusters span ~2*run_rcut, so every one
    tripped ``diameter >= 2*rcut``. The fix is to set ``GateThresholds.rcut`` to the
    run's rcut, never to loosen the gate.
    """
    diameter = pe.proj_report.diameter
    limit = 2.0 * rcut
    if not math.isfinite(diameter):
        return GateResult("G7", GateOutcome.FAIL, f"COLLISION: diameter={diameter}", diameter)
    if diameter >= limit:
        return GateResult(
            "G7",
            GateOutcome.FAIL,
            f"STRADDLING_CLUSTER: diameter={diameter:.3f} >= 2*rcut={limit:.3f} — "
            f"if (nearly) all events fail G7, thresholds.rcut ({rcut:.1f} A) is smaller "
            f"than the pyKMC run's rcut (cluster diameter ~= 2*run_rcut; implied run "
            f"rcut ~= {diameter / 2.0:.1f} A); set GateThresholds.rcut to the run's rcut",
            diameter,
        )
    return GateResult(
        "G7", GateOutcome.PASS, f"diameter={diameter:.3f} < 2*rcut={limit:.3f}", diameter
    )


def run_gates(
    pe: ProjectedEvent,
    *,
    thresholds: GateThresholds,
    linked_bwd: ProjectedEvent | None = None,
    t_ref_K: float = 500.0,
) -> tuple[GateResult, ...]:
    """Run gates G1-G7 for one event, in order (contract 2.7).

    ``t_ref_K`` (campaign default 500 K) is required for the T-dependent detailed
    balance gate G2; the section-2.7 signature omitted it, so it is a keyword with
    a default here.
    """
    return (
        gate_g1_barrier_bounds(
            pe, thresholds.emin_event, thresholds.emax_event, thresholds.backward_emin_event
        ),
        gate_g2_detailed_balance(pe, linked_bwd, t_ref_K, thresholds.db_tol),
        gate_g3_snap_residual(pe, thresholds.mover_snap_tol),
        gate_g4_round_trip(pe),
        gate_g5_conservation(pe),
        gate_g6_context_completeness(pe),
        gate_g7_cluster_integrity(pe, thresholds.rcut),
    )


# --------------------------------------------------------------------------- #
# 2.8 Catalogue assembly                                                      #
# --------------------------------------------------------------------------- #
def _member_key(pe: ProjectedEvent) -> tuple[float, float, int, int, str]:
    """Deterministic total-order key for sorting a class's members."""
    nu0 = pe.nu0_fwd_hz if math.isfinite(pe.nu0_fwd_hz) else float("inf")
    return (pe.Ea_fwd_eV, nu0, pe.source_row, pe.idx_ref, pe.event_id)


def _transform_offset(off: Offset, anchor: Offset, mat: Any) -> Offset:
    """Apply ``T(x) = mat @ (x - anchor)`` with an integer 3x3 SymOp matrix."""
    d0 = off[0] - anchor[0]
    d1 = off[1] - anchor[1]
    d2 = off[2] - anchor[2]
    return (
        int(mat[0][0] * d0 + mat[0][1] * d1 + mat[0][2] * d2),
        int(mat[1][0] * d0 + mat[1][1] * d1 + mat[1][2] * d2),
        int(mat[2][0] * d0 + mat[2][1] * d1 + mat[2][2] * d2),
    )


def _anchor_pred(context: tuple[StencilSite, ...]) -> OccPredicate:
    """Best-effort rarest predicate over the context (contract 5.2 anchor_pred)."""
    if not context:
        return OccPredicate(kind="WILDCARD")
    counts: Counter[tuple[str, tuple[int, ...]]] = Counter()
    reps: dict[tuple[str, tuple[int, ...]], OccPredicate] = {}
    for cs in context:
        key = (cs.pred.kind, tuple(sorted(int(s) for s in cs.pred.species)))
        counts[key] += 1
        reps.setdefault(key, cs.pred)
    best_key = min(
        counts,
        key=lambda k: (counts[k], _pred_store_code(reps[k]), k[0], k[1]),
    )
    return reps[best_key]


def _canonical_orientation(
    rep: ProjectedEvent, canonical: Any
) -> tuple[tuple[DeltaSite, ...], tuple[StencilSite, ...], tuple[PathToken, ...]]:
    """Re-express rep's delta/context/tokens into the winning ``(a*, g*)`` frame.

    Uses ``canonical.argmin_orientation`` + the returned ``SymOp`` matrix and
    ``canonical.canonical_rank_map`` for token ordering. Falls back to rep's own
    frame if those A5 helpers are unavailable (best-effort; identity of record is
    ``canonical_blob``).
    """
    try:
        anchor, gop = canonical.argmin_orientation(rep)
        mat = gop.mat
        delta = tuple(
            DeltaSite(_transform_offset(ds.off, anchor, mat), ds.before, ds.after)
            for ds in rep.delta
        )
        context = tuple(
            StencilSite(_transform_offset(cs.off, anchor, mat), cs.pred) for cs in rep.context
        )
        try:
            ranks = canonical.canonical_rank_map(rep.movers, anchor, gop)
            toks = [
                PathToken(int(ranks[m]), tok.kind, tuple(tok.coord_sig))
                for m, tok in zip(rep.movers, rep.saddle_tokens, strict=False)
            ]
            toks.sort(key=lambda t: t.start_rank)
            saddle_token = tuple(toks)
        except Exception:  # noqa: BLE001 - rank map unavailable -> keep given order
            saddle_token = rep.saddle_tokens
        return delta, context, saddle_token
    except Exception:  # noqa: BLE001 - argmin unavailable -> rep frame
        return rep.delta, rep.context, rep.saddle_tokens


# Systematic rcut-mismatch heuristic (contract 8 — additive diagnostics only, never
# a gate outcome): flag when >= _G7_MISMATCH_MIN_EVENTS events are ingested and at
# least _G7_MISMATCH_FAIL_FRACTION of them FAIL G7. See the 2026-07-17 incident in
# ``gate_g7_cluster_integrity`` / ``_flag_rcut_mismatch``.
_G7_MISMATCH_MIN_EVENTS: int = 10
_G7_MISMATCH_FAIL_FRACTION: float = 0.9


@dataclass
class CatalogueReport:
    """Additive aggregate diagnostics for :func:`build_class_catalogue`.

    Purely a *report* channel: filling it never changes ``class_id``, serialization,
    or any gate outcome (contract 8). ``build_class_catalogue`` populates a
    caller-supplied instance in place; a user who passes nothing still gets the
    :func:`warnings.warn` surface. ``rcut_mismatch_suspected`` flags the 2026-07-17
    production_NiCrFe failure mode -- near-total G7 STRADDLING because
    ``thresholds.rcut`` is smaller than the pyKMC run's rcut (a config mismatch, not
    bad data; the fix is to raise ``GateThresholds.rcut``, never to loosen the gate).
    """

    n_events: int = 0
    n_classes: int = 0
    n_g7_fail: int = 0
    g7_fail_fraction: float = 0.0
    median_cluster_diameter_A: float = float("nan")
    rcut_configured_A: float = float("nan")
    implied_run_rcut_A: float = float("nan")
    rcut_mismatch_suspected: bool = False
    rcut_mismatch_message: str | None = None


def build_class_catalogue(
    events: Sequence[ProjectedEvent],
    *,
    t_ref_K: float,
    thresholds: GateThresholds,
    nu0_fallback_hz: float,
    first_seen_cycle: int = 0,
    report: CatalogueReport | None = None,
) -> list[EventClass]:
    """Assemble ``EventClass`` rows from projected events (contract 2.8).

    Groups ``ProjectedEvent``s by ``class_id`` (via ``canonical.class_id``, lazy
    import), aggregates rates over each class's **sorted** members, links backward
    classes (``idx_backward`` / ``id_saddle``), computes ``dE_pair_list`` +
    ``dEnergy``, runs all gates, sets ``audit_status``, and returns the rows sorted
    by ``class_id``. Deterministic: grouping and reductions use sorted keys.

    ``audit_status`` is ``approved`` iff every aggregated gate is PASS/NA and the
    class is corroborated by >= 2 members (a singleton is an unconfirmed
    first-instance -> ``pending``, matching contract 8's "first-instance routes to
    audit"); otherwise ``pending``.

    ``report`` (optional, additive): when supplied, it is filled in place with
    aggregate diagnostics -- notably ``rcut_mismatch_suspected`` for the near-total
    G7 STRADDLING failure mode (see :func:`_flag_rcut_mismatch`). The report channel
    never changes ``class_id``, serialization, or any gate outcome.
    """
    from pylatkmc.ingest import canonical

    # index every event by idx_ref (deterministic: smallest source_row wins ties)
    by_idx_ref: dict[int, ProjectedEvent] = {}
    for pe in sorted(events, key=lambda p: p.source_row):
        by_idx_ref.setdefault(pe.idx_ref, pe)

    groups: dict[str, list[ProjectedEvent]] = {}
    for pe in events:
        cid = canonical.class_id(pe)
        groups.setdefault(cid, []).append(pe)

    out: list[EventClass] = []
    for cid in sorted(groups):
        members = sorted(groups[cid], key=_member_key)
        rep = members[0]

        cf = canonical.canonical_form(rep)
        blob = canonical.canonical_blob(cf)
        delta_c, context_c, saddle_c = _canonical_orientation(rep, canonical)

        barriers = tuple(m.Ea_fwd_eV for m in members)
        nu0_f = tuple(m.nu0_fwd_hz for m in members)
        mover_resid = tuple(m.proj_report.mover_max_residual for m in members)
        max_resid = tuple(m.proj_report.max_residual for m in members)

        # backward linking
        nu0_b_vals: list[float] = []
        dE_pairs: list[float] = []
        # (k_f, k_b, nu0_f, nu0_b) per linked member -> class-level G2 (contract 8).
        ratio_terms: list[tuple[float, float, float, float]] = []
        backward_cids: list[tuple[tuple[float, float, int, int, str], str]] = []
        for m in members:
            partner = by_idx_ref.get(m.idx_backward) if m.idx_backward >= 0 else None
            if partner is not None:
                nu0_b_vals.append(partner.nu0_fwd_hz)
                dE_pairs.append(m.Ea_fwd_eV - partner.Ea_fwd_eV)
                ratio_terms.append((m.k_row, partner.k_row, m.nu0_fwd_hz, partner.nu0_fwd_hz))
                backward_cids.append((_member_key(m), canonical.class_id(partner)))
            else:
                nu0_b_vals.append(float("nan"))

        self_reverse = bool(canonical.is_self_reverse(rep))
        backward_class: str | None = None
        if backward_cids:
            backward_cids.sort(key=lambda kv: kv[0])
            backward_class = backward_cids[0][1]
        if self_reverse:
            pair_status: Literal["linked", "synthesized_balanced", "self", "unpaired"] = "self"
        elif dE_pairs:
            pair_status = "linked"
        else:
            pair_status = "unpaired"
        dEnergy = float(np.mean(dE_pairs)) if dE_pairs else None

        agg = aggregate_rate_space(
            list(barriers), list(nu0_f), t_ref_K, nu0_fallback_hz=nu0_fallback_hz
        )

        # gates: run per member, aggregate to the worst outcome per gate, then fold
        # in the class-level G2 (the fold-in detector the per-pair form cannot express).
        gate_log = _aggregate_gates(members, by_idx_ref, thresholds, t_ref_K)
        g2_class = gate_g2_pair_spread(dE_pairs, ratio_terms, t_ref_K, thresholds.db_tol)
        gate_log = _merge_gate(gate_log, g2_class)
        gate_ok = all(g.outcome in (GateOutcome.PASS, GateOutcome.NA) for g in gate_log)
        audit_status: Literal["approved", "pending", "rejected", "quarantined"] = (
            "approved" if gate_ok and len(members) >= 2 else "pending"
        )

        out.append(
            EventClass(
                class_id=cid,
                canonical_form=cf,
                canonical_blob=blob,
                depth_sig=rep.depth_sig,
                coloring=rep.coloring,
                move_shape=int(canonical.move_shape(rep)),
                family_id=int(canonical.family_id(rep)),
                delta=delta_c,
                delta_atoms=rep.delta_atoms,
                context=context_c,
                saddle_token=saddle_c,
                orientation_count=int(canonical.orientation_count(rep)),
                r_ctx_used=rep.r_ctx_used,
                r_id_used=rep.r_ctx_used,
                anchor_pred=_anchor_pred(context_c),
                t_ref_K=t_ref_K,
                barriers_eV=barriers,
                nu0_f_list_hz=nu0_f,
                nu0_b_list_hz=tuple(nu0_b_vals),
                dE_pair_list_eV=tuple(dE_pairs),
                mover_max_residual_list=mover_resid,
                max_residual_list=max_resid,
                k_rate_mean_psinv=agg.k_rate_mean_psinv,
                Ea_rep_eV=agg.Ea_rep_eV,
                nu0_geo_psinv=agg.nu0_geo_psinv,
                Ea_std_eV=agg.Ea_std_eV,
                n_eff=agg.n_eff,
                Ea_mean_eV=agg.Ea_mean_eV,
                Ea_median_eV=agg.Ea_median_eV,
                backward_class=backward_class,
                self_reverse=self_reverse,
                dEnergy_eV=dEnergy,
                pair_status=pair_status,
                source_rows=tuple(sorted(m.source_row for m in members)),
                source_idx_refs=tuple(sorted(m.idx_ref for m in members)),
                source_sim_paths=(),
                first_seen_cycle=first_seen_cycle,
                gate_log=gate_log,
                audit_status=audit_status,
            )
        )

    out.sort(key=lambda ec: ec.class_id)
    _flag_rcut_mismatch(events, out, thresholds, report)
    return out


def _flag_rcut_mismatch(
    events: Sequence[ProjectedEvent],
    classes: Sequence[EventClass],
    thresholds: GateThresholds,
    report: CatalogueReport | None,
) -> None:
    """Warn (and fill ``report``) when near-total G7 failure implies rcut is too small.

    Additive heuristic (contract 8): a *configuration* mismatch, not bad data, is the
    #1 cause of a wholesale G7 rejection. On 2026-07-17 the first real ingest of
    ``production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle`` FAILed G7 on
    445/445 rows because ``GateThresholds.rcut`` defaulted to 5.0 A while the pyKMC run
    used rcut ~= 8 A -- every reference cluster (diameter ~= 2*run_rcut) tripped the
    ``diameter >= 2*rcut`` gate. When >= ``_G7_MISMATCH_MIN_EVENTS`` events are ingested
    and >= ``_G7_MISMATCH_FAIL_FRACTION`` of them FAIL G7, surface the actionable fix.
    This is diagnostics only: it never touches a gate outcome, ``class_id``, or
    serialization.
    """
    n_events = len(events)
    n_g7_fail = sum(
        1
        for pe in events
        if gate_g7_cluster_integrity(pe, thresholds.rcut).outcome == GateOutcome.FAIL
    )
    frac = (n_g7_fail / n_events) if n_events else 0.0
    # sort before the median reduction (deterministic, order-independent — contract 0).
    finite_diams = sorted(
        pe.proj_report.diameter for pe in events if math.isfinite(pe.proj_report.diameter)
    )
    median_d = float(np.median(finite_diams)) if finite_diams else float("nan")
    implied_run_rcut = median_d / 2.0

    suspected = n_events >= _G7_MISMATCH_MIN_EVENTS and frac >= _G7_MISMATCH_FAIL_FRACTION
    message: str | None = None
    if suspected:
        message = (
            f"rcut_mismatch_suspected: {n_g7_fail}/{n_events} events FAIL G7 "
            f"(STRADDLING_CLUSTER); configured GateThresholds.rcut="
            f"{thresholds.rcut:.3f} A, median cluster diameter={median_d:.3f} A implies "
            f"a pyKMC run rcut ~= {implied_run_rcut:.3f} A — set GateThresholds.rcut to "
            f"the pyKMC run's rcut and re-ingest"
        )
        warnings.warn(message, stacklevel=3)

    if report is not None:
        report.n_events = n_events
        report.n_classes = len(classes)
        report.n_g7_fail = n_g7_fail
        report.g7_fail_fraction = frac
        report.median_cluster_diameter_A = median_d
        report.rcut_configured_A = thresholds.rcut
        report.implied_run_rcut_A = implied_run_rcut
        report.rcut_mismatch_suspected = suspected
        report.rcut_mismatch_message = message


def _merge_gate(gate_log: tuple[GateResult, ...], override: GateResult) -> tuple[GateResult, ...]:
    """Replace ``override.gate``'s entry with the worse (higher-severity) of the two.

    Used to fold the class-level G2 (fold-in detector) into the per-member gate log:
    a class-level FAIL wins over a per-member PASS/NA, but a per-member FAIL (e.g. a
    stored-``k`` inconsistency) is not masked by a class-level PASS/NA.
    """
    out: list[GateResult] = []
    for g in gate_log:
        if g.gate == override.gate and (
            _OUTCOME_SEVERITY[override.outcome] > _OUTCOME_SEVERITY[g.outcome]
        ):
            out.append(override)
        else:
            out.append(g)
    return tuple(out)


def _aggregate_gates(
    members: Sequence[ProjectedEvent],
    by_idx_ref: dict[int, ProjectedEvent],
    thresholds: GateThresholds,
    t_ref_K: float,
) -> tuple[GateResult, ...]:
    """Run all gates over every member; keep the worst outcome per gate."""
    worst: dict[int, GateResult] = {}
    for m in members:
        partner = by_idx_ref.get(m.idx_backward) if m.idx_backward >= 0 else None
        results = run_gates(m, thresholds=thresholds, linked_bwd=partner, t_ref_K=t_ref_K)
        for i, res in enumerate(results):
            cur = worst.get(i)
            if cur is None or _OUTCOME_SEVERITY[res.outcome] > _OUTCOME_SEVERITY[cur.outcome]:
                worst[i] = res
    return tuple(worst[i] for i in range(len(worst)))


# --------------------------------------------------------------------------- #
# 2.8 / 9 Parquet I/O                                                         #
# --------------------------------------------------------------------------- #
def _pred_store_code(pred: OccPredicate) -> int:
    """Coloring-invariant, species-preserving store code for a predicate.

    Round-trips context predicates losslessly regardless of coloring (coloring
    affects only ``canonical_blob`` / ``class_id``, not the stored provenance
    context). ``SPECIES`` stores its single species int; sentinels their code.
    """
    if pred.kind == "EMPTY":
        return int(Occ.EMPTY)
    if pred.kind == "OUTSIDE":
        return int(Occ.OUTSIDE)
    if pred.kind == "WILDCARD":
        return 253
    if pred.kind == "OCC_ANY":
        return int(Occ.OCC_ANY)
    if pred.kind == "SPECIES":
        if not pred.species:
            raise ValueError("SPECIES predicate with empty species set")
        return int(min(pred.species))
    raise ValueError(f"unknown OccPredicate kind: {pred.kind!r}")


def _pred_from_store_code(code: int) -> OccPredicate:
    """Inverse of ``_pred_store_code``."""
    if code == int(Occ.EMPTY):
        return OccPredicate(kind="EMPTY")
    if code == int(Occ.OUTSIDE):
        return OccPredicate(kind="OUTSIDE")
    if code == 253:
        return OccPredicate(kind="WILDCARD")
    if code == int(Occ.OCC_ANY):
        return OccPredicate(kind="OCC_ANY")
    return OccPredicate(kind="SPECIES", species=frozenset({Occ(code)}))


def catalogue_arrow_schema() -> pa.Schema:
    """The fixed-order pyarrow schema for the ``EventClass`` catalogue (contract 9)."""
    import pyarrow as pa

    delta_type = pa.list_(
        pa.struct(
            [
                ("dx", pa.int32()),
                ("dy", pa.int32()),
                ("dz", pa.int32()),
                ("before", pa.int8()),
                ("after", pa.int8()),
            ]
        )
    )
    context_type = pa.list_(
        pa.struct(
            [("dx", pa.int32()), ("dy", pa.int32()), ("dz", pa.int32()), ("pred", pa.int16())]
        )
    )
    saddle_type = pa.list_(
        pa.struct(
            [
                ("start_rank", pa.int32()),
                ("kind", pa.string()),
                ("coord_sig", pa.list_(pa.int32())),
            ]
        )
    )
    gate_type = pa.list_(
        pa.struct(
            [
                ("gate", pa.string()),
                ("outcome", pa.int8()),
                ("detail", pa.string()),
                ("value", pa.float64()),
            ]
        )
    )
    return pa.schema(
        [
            ("class_id", pa.string()),
            ("canonical_blob", pa.binary()),
            ("schema_version", pa.int32()),
            ("coloring", pa.string()),
            ("depth_sig_kind", pa.string()),
            ("depth_sig_param", pa.int32()),
            ("move_shape", pa.int64()),
            ("family_id", pa.int64()),
            ("delta_atoms", pa.int32()),
            ("orientation_count", pa.int32()),
            ("r_ctx_used", pa.float64()),
            ("r_id_used", pa.float64()),
            ("anchor_pred", pa.string()),
            ("delta", delta_type),
            ("context", context_type),
            ("saddle_token", saddle_type),
            ("t_ref_K", pa.float64()),
            ("barriers_eV", pa.list_(pa.float64())),
            ("nu0_f_list_hz", pa.list_(pa.float64())),
            ("nu0_b_list_hz", pa.list_(pa.float64())),
            ("dE_pair_list_eV", pa.list_(pa.float64())),
            ("k_rate_mean_psinv", pa.float64()),
            ("Ea_rep_eV", pa.float64()),
            ("nu0_geo_psinv", pa.float64()),
            ("Ea_std_eV", pa.float64()),
            ("n_eff", pa.float64()),
            ("Ea_mean_eV", pa.float64()),
            ("Ea_median_eV", pa.float64()),
            ("backward_class", pa.string()),
            ("self_reverse", pa.bool_()),
            ("dEnergy_eV", pa.float64()),
            ("pair_status", pa.string()),
            ("source_rows", pa.list_(pa.int64())),
            ("source_idx_refs", pa.list_(pa.int64())),
            ("source_sim_paths", pa.list_(pa.string())),
            ("first_seen_cycle", pa.int32()),
            ("audit_status", pa.string()),
            ("gate_log", gate_type),
            # --- schema v2: previously-omitted [C] fields + human-veto reason ---
            ("audit_reason", pa.string()),
            ("phi", pa.list_(pa.float64())),
            ("model_version", pa.string()),
            ("dE_model_version", pa.string()),
            ("nu0_pair_policy", pa.string()),
            # fallback_stats is a heterogeneous tuple (leverage, hull_flag,
            # model_version, tier) — serialized as a JSON string column.
            ("fallback_stats", pa.string()),
            # --- schema v3: per-member snap residuals (Å, aligned with barriers_eV;
            # memo 2026-07-29 §11) ---
            ("mover_max_residual_list", pa.list_(pa.float64())),
            ("max_residual_list", pa.list_(pa.float64())),
        ]
    )


def _pred_to_str(pred: OccPredicate) -> str:
    """Stable, parseable string form of a predicate for the ``anchor_pred`` column."""
    if pred.kind == "SPECIES":
        codes = ",".join(str(int(s)) for s in sorted(pred.species))
        return f"SPECIES[{codes}]"
    return pred.kind


def _pred_from_str(text: str) -> OccPredicate:
    """Inverse of ``_pred_to_str``."""
    if text.startswith("SPECIES["):
        body = text[len("SPECIES[") : -1]
        codes = frozenset(Occ(int(c)) for c in body.split(",") if c != "")
        return OccPredicate(kind="SPECIES", species=codes)
    return OccPredicate(kind=text)  # type: ignore[arg-type]


def _fallback_stats_to_json(fs: tuple[Any, ...]) -> str | None:
    """Serialize the [C] ``fallback_stats`` tuple as a JSON string column.

    Contract shape is ``(leverage, hull_flag, model_version, tier)`` — a
    heterogeneous flat tuple, so a JSON string is the schema-stable carrier. An
    empty tuple (the Phase A/B default) stores ``None`` and round-trips back to
    ``()``.
    """
    if not fs:
        return None
    return json.dumps(list(fs))


def _fallback_stats_from_json(text: str | None) -> tuple[Any, ...]:
    """Inverse of :func:`_fallback_stats_to_json` (``None``/empty -> ``()``)."""
    if not text:
        return ()
    return tuple(json.loads(text))


def _event_to_row(ec: EventClass) -> dict[str, Any]:
    """One ``EventClass`` -> a dict of column values matching the arrow schema."""
    return {
        "class_id": ec.class_id,
        "canonical_blob": ec.canonical_blob,
        "schema_version": int(ec.schema_version),
        "coloring": Coloring(ec.coloring).name.lower(),
        "depth_sig_kind": DepthKind(ec.depth_sig.kind).name,
        "depth_sig_param": int(ec.depth_sig.param),
        "move_shape": int(ec.move_shape),
        "family_id": int(ec.family_id),
        "delta_atoms": int(ec.delta_atoms),
        "orientation_count": int(ec.orientation_count),
        "r_ctx_used": float(ec.r_ctx_used),
        "r_id_used": float(ec.r_id_used),
        "anchor_pred": _pred_to_str(ec.anchor_pred),
        "delta": [
            {
                "dx": int(ds.off[0]),
                "dy": int(ds.off[1]),
                "dz": int(ds.off[2]),
                "before": int(ds.before),
                "after": int(ds.after),
            }
            for ds in ec.delta
        ],
        "context": [
            {
                "dx": int(cs.off[0]),
                "dy": int(cs.off[1]),
                "dz": int(cs.off[2]),
                "pred": _pred_store_code(cs.pred),
            }
            for cs in ec.context
        ],
        "saddle_token": [
            {
                "start_rank": int(tok.start_rank),
                "kind": SaddleKind(tok.kind).name,
                "coord_sig": [int(c) for c in tok.coord_sig],
            }
            for tok in ec.saddle_token
        ],
        "t_ref_K": float(ec.t_ref_K),
        "barriers_eV": [float(x) for x in ec.barriers_eV],
        "nu0_f_list_hz": [float(x) for x in ec.nu0_f_list_hz],
        "nu0_b_list_hz": [float(x) for x in ec.nu0_b_list_hz],
        "dE_pair_list_eV": [float(x) for x in ec.dE_pair_list_eV],
        "k_rate_mean_psinv": float(ec.k_rate_mean_psinv),
        "Ea_rep_eV": float(ec.Ea_rep_eV),
        "nu0_geo_psinv": float(ec.nu0_geo_psinv),
        "Ea_std_eV": None if ec.Ea_std_eV is None else float(ec.Ea_std_eV),
        "n_eff": float(ec.n_eff),
        "Ea_mean_eV": float(ec.Ea_mean_eV),
        "Ea_median_eV": float(ec.Ea_median_eV),
        "backward_class": ec.backward_class,
        "self_reverse": bool(ec.self_reverse),
        "dEnergy_eV": None if ec.dEnergy_eV is None else float(ec.dEnergy_eV),
        "pair_status": ec.pair_status,
        "source_rows": [int(x) for x in ec.source_rows],
        "source_idx_refs": [int(x) for x in ec.source_idx_refs],
        "source_sim_paths": [str(x) for x in ec.source_sim_paths],
        "first_seen_cycle": int(ec.first_seen_cycle),
        "audit_status": ec.audit_status,
        "gate_log": [
            {
                "gate": g.gate,
                "outcome": int(g.outcome),
                "detail": g.detail,
                "value": None if g.value is None else float(g.value),
            }
            for g in ec.gate_log
        ],
        # --- schema v2: previously-omitted [C] fields + human-veto reason ---
        "audit_reason": ec.audit_reason,
        "phi": [float(x) for x in ec.phi],
        "model_version": ec.model_version,
        "dE_model_version": ec.dE_model_version,
        "nu0_pair_policy": ec.nu0_pair_policy,
        "fallback_stats": _fallback_stats_to_json(ec.fallback_stats),
        # --- schema v3: per-member snap residuals ---
        "mover_max_residual_list": [float(x) for x in ec.mover_max_residual_list],
        "max_residual_list": [float(x) for x in ec.max_residual_list],
    }


def write_catalogue_parquet(
    classes: Sequence[EventClass],
    path: str | Path,
    *,
    metadata: Mapping[bytes, bytes] | None = None,
) -> None:
    """Write ``EventClass`` rows to Parquet, sorted by ``class_id`` (contract 9).

    ``metadata`` (optional) is attached as file-level (arrow schema) key/value
    metadata — e.g. the ingest-QC conditions stamp under
    ``b"pylatkmc.qc.conditions"``. It never affects the column data.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    schema = catalogue_arrow_schema()
    ordered = sorted(classes, key=lambda ec: ec.class_id)
    rows = [_event_to_row(ec) for ec in ordered]
    columns = {
        field.name: pa.array([row[field.name] for row in rows], type=field.type) for field in schema
    }
    if metadata is not None:
        schema = schema.with_metadata(dict(metadata))
    table = pa.Table.from_pydict(columns, schema=schema)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


def _row_to_event(row: dict[str, Any]) -> EventClass:
    """One Parquet row dict -> reconstructed ``EventClass``."""
    coloring = Coloring.GREY if row["coloring"] == "grey" else Coloring.FULL
    depth_sig = DepthSig(DepthKind[row["depth_sig_kind"]], int(row["depth_sig_param"]))
    delta = tuple(
        DeltaSite(
            (int(d["dx"]), int(d["dy"]), int(d["dz"])),
            Occ(int(d["before"])),
            Occ(int(d["after"])),
        )
        for d in row["delta"]
    )
    context = tuple(
        StencilSite(
            (int(c["dx"]), int(c["dy"]), int(c["dz"])), _pred_from_store_code(int(c["pred"]))
        )
        for c in row["context"]
    )
    saddle_token = tuple(
        PathToken(
            int(t["start_rank"]),
            SaddleKind[t["kind"]],
            tuple(int(x) for x in t["coord_sig"]),
        )
        for t in row["saddle_token"]
    )
    gate_log = tuple(
        GateResult(
            g["gate"],
            GateOutcome(int(g["outcome"])),
            g["detail"],
            None if g["value"] is None else float(g["value"]),
        )
        for g in row["gate_log"]
    )
    return EventClass(
        class_id=row["class_id"],
        canonical_form=decode_canonical_blob(row["canonical_blob"]),
        canonical_blob=row["canonical_blob"],
        depth_sig=depth_sig,
        coloring=coloring,
        move_shape=int(row["move_shape"]),
        family_id=int(row["family_id"]),
        delta=delta,
        delta_atoms=int(row["delta_atoms"]),
        context=context,
        saddle_token=saddle_token,
        orientation_count=int(row["orientation_count"]),
        r_ctx_used=float(row["r_ctx_used"]),
        r_id_used=float(row["r_id_used"]),
        anchor_pred=_pred_from_str(row["anchor_pred"]),
        t_ref_K=float(row["t_ref_K"]),
        barriers_eV=tuple(float(x) for x in row["barriers_eV"]),
        nu0_f_list_hz=tuple(float(x) for x in row["nu0_f_list_hz"]),
        nu0_b_list_hz=tuple(float(x) for x in row["nu0_b_list_hz"]),
        dE_pair_list_eV=tuple(float(x) for x in row["dE_pair_list_eV"]),
        k_rate_mean_psinv=float(row["k_rate_mean_psinv"]),
        Ea_rep_eV=float(row["Ea_rep_eV"]),
        nu0_geo_psinv=float(row["nu0_geo_psinv"]),
        Ea_std_eV=None if row["Ea_std_eV"] is None else float(row["Ea_std_eV"]),
        n_eff=float(row["n_eff"]),
        Ea_mean_eV=float(row["Ea_mean_eV"]),
        Ea_median_eV=float(row["Ea_median_eV"]),
        backward_class=row["backward_class"],
        self_reverse=bool(row["self_reverse"]),
        dEnergy_eV=None if row["dEnergy_eV"] is None else float(row["dEnergy_eV"]),
        pair_status=row["pair_status"],
        source_rows=tuple(int(x) for x in row["source_rows"]),
        source_idx_refs=tuple(int(x) for x in row["source_idx_refs"]),
        source_sim_paths=tuple(str(x) for x in row["source_sim_paths"]),
        first_seen_cycle=int(row["first_seen_cycle"]),
        gate_log=gate_log,
        audit_status=row["audit_status"],
        # schema-v2 columns; absent in a v1 parquet -> field defaults (back-compat).
        audit_reason=row.get("audit_reason") or "",
        phi=tuple(float(x) for x in (row.get("phi") or ())),
        model_version=row.get("model_version"),
        dE_model_version=row.get("dE_model_version"),
        nu0_pair_policy=row.get("nu0_pair_policy"),
        fallback_stats=_fallback_stats_from_json(row.get("fallback_stats")),
        # schema-v3 columns; absent in a v1/v2 parquet -> field defaults (back-compat).
        mover_max_residual_list=tuple(float(x) for x in (row.get("mover_max_residual_list") or ())),
        max_residual_list=tuple(float(x) for x in (row.get("max_residual_list") or ())),
        schema_version=int(row["schema_version"]),
    )


def read_catalogue_parquet(path: str | Path) -> list[EventClass]:
    """Read a catalogue Parquet file back into ``EventClass`` rows (contract 9)."""
    import pyarrow.parquet as pq

    table = pq.read_table(Path(path))
    rows = table.to_pylist()
    return [_row_to_event(row) for row in rows]
