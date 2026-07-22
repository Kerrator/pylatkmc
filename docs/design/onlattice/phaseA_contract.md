# Phase A interface contract — pylatkmc ingest v2 (event-representation layer)

**Status:** authoritative build contract for Phase A of the hybrid plan in
`COMPARISON.md` §4. Implements the ingest-side subset of `FINAL_DESIGN.md`
(§1.1–1.3, §2, §3, §4, §6.1, §8, §12, §14). Five feature agents + one integration
agent implement the modules below **without cross-talk**; this document is the only
shared reference. Where this contract and `FINAL_DESIGN.md` differ, **this contract
wins for Phase A** (deviations are listed in §12 with justification).

**Scope in.** New flat modules in `pylatkmc/pylatkmc/ingest/`: `lattice.py`,
`event_class.py`, `projection.py`, `event_projection.py`, `canonical.py`; the §6.1
rate-space edit to the existing `build_family_rate_table.py`; the `EventClass`
Parquet catalogue; pure-math + data-dependent tests.

**Scope out (do NOT touch / do NOT implement).** pylatkmc core (codegen, runtime,
translator, `spec.py`, `processes.py`), `FAMILY_REGISTRY`/`families.py` (stays as a
reporting view — read-only), the fallback regressor (§6.2), the loop driver, coverage
reports, the runtime grid SoA (`Grid`), the grid-level reverse map beyond the small
deterministic `to_atomistic` in `projection.py`, and the `sym_matrix`/`sym_perm`
realizability cross-check (§4.7 — deferred; leave a stub hook only).

---

## 0. Global conventions (every agent obeys these)

### 0.1 Determinism (hard gate — CI + `pylatkmc/CLAUDE.md`)
- **No `hash()`, no `set`/`dict` iteration, no `PYTHONHASHSEED` dependence** anywhere
  that affects a `class_id`, a rate, an `orientation_count`, a Parquet row order, or a
  gate outcome. Use `sorted(...)` with explicit total-order keys and stable tuple
  comparison.
- Identity/aggregation digests use **`hashlib.blake2b`**, never `hash()`.
- Any floating tie-break in identity is forbidden: identity is computed over **integer**
  lattice offsets and **integer categorical codes** only. Floats appear only in rates and
  in the projection residual pre-filters, never in a `class_id`.
- Reductions over member lists (rate aggregation, orbit dedup) iterate a **sorted** list.

### 0.2 Module-load dependency DAG (prevents import cycles)
Load-time (module-level) imports form this DAG; violating it is a review failure:

```
lattice.py          -> (numpy, stdlib) only
event_class.py      -> (numpy, stdlib; pandas/pyarrow lazily inside I/O fns) only
projection.py       -> lattice, event_class
event_projection.py -> lattice, event_class
canonical.py        -> lattice, event_class
```

`event_class.py`'s *assembly* helpers (`build_class_catalogue`, `link_backward`,
`gate_g2`, `gate_g4`) need `canonical` and `event_projection`. **Import those two
modules lazily (inside the function body), never at module top level**, e.g.
`from pylatkmc.ingest import canonical`. This keeps the load DAG acyclic while letting
the schema owner own the assembly path. `canonical.py` and `event_projection.py` may
import `event_class` **types** at module level (safe: `event_class` never imports them
at load time).

### 0.3 Typing, lint, docstrings
- Python 3.10–3.13. Full type annotations (strict mypy, advisory in CI but keep it
  clean). Use `from __future__ import annotations` at the top of every file.
- Ruff: double quotes, docstrings required (`E,F,W,I,UP,B,SIM`, line-length 100,
  `E501` ignored). `pylatkmc/ingest/**` already whitelists `B028,F841`.
- Dataclasses: `@dataclass(frozen=True)` for value types (predicates, offsets, tokens,
  canonical forms). `EventClass` is `@dataclass` (mutable during assembly), but treat it
  as write-once.

### 0.4 Constants and their single sources
- **kB**: `from pylatkmc.rate_expression import KB_EV_PER_K` (= `8.617333e-5` eV/K).
  Do **not** define a second kB (respects the `pylatkmc/CLAUDE.md` invariant). `ingest`
  importing core is allowed (dependency direction is ingest→core; core never imports
  ingest).
- **Hz↔ps⁻¹**: `HZ_PER_PSINV = 1.0e12` (module constant in `event_class.py`). The
  on-lattice rate unit is **ps⁻¹** (per the `pykmc-k0-units-clock-freeze` project note:
  pyKMC `[RateConstant] k0` is ps⁻¹, not Hz). pyKMC HTST `nu0` / `k_prefactor` are in
  **Hz**; convert on output (÷`HZ_PER_PSINV`).
- **Lattice**: `A_NOMINAL = 3.52` Å, `H = A_NOMINAL / 2`. Occupancy/kind/depth integer
  codes are defined once in `event_class.py` (§2 below) and imported everywhere.
- **Serialization version**: `CANON_SCHEMA_VERSION = 1` (in `canonical.py`);
  `CATALOGUE_SCHEMA_VERSION = 1` (in `event_class.py`). Bumping either changes all keys /
  the Parquet schema deliberately. *(2026-07-21)* The Phase C rate-model fields
  (`phi`-as-E_sym, `dE_model_version`, `nu0_pair_policy`, restructured `fallback_stats`)
  land under `CATALOGUE_SCHEMA_VERSION = 2`; Phase A/B parquets stay at 1.

### 0.5 pyKMC columns consumed (from `FINAL_DESIGN.md` §14 / `event_table.py:718-737`)
Phase A reads **only** these reference-table columns (verified present):
`idx_ref, event_id, initial_positions, initial_types, saddle_positions,
final_positions, energy_barrier, k, k_prefactor, id_saddle, id_final, move_atom_idx,
sym_matrix, sym_perm, idx_backward, dra`, and `nu0` **iff HTST was active**. Clusters
are stored **raw-wrapped, subset-relative, un-recentred** — every cluster must be
min-image-unwrapped about `move_atom_idx` before use (§3, Geom-1).

---

## 1. Ownership map (no file is owned by two agents)

| Agent | Owns (writes) | Also owns tests |
|---|---|---|
| **A1 — Lattice** | `ingest/lattice.py` | `tests/unit_py/test_ingest_lattice.py` |
| **A2 — Schema/Rate/Curation** | `ingest/event_class.py`; **edit** `ingest/build_family_rate_table.py` | `tests/unit_py/test_ingest_rate_agg.py`, `tests/unit_py/test_ingest_parquet.py`, `tests/ingest/test_rate_space_table.py` |
| **A3 — Forward projection** | `ingest/projection.py` | `tests/unit_py/test_ingest_projection.py` |
| **A4 — Event projection** | `ingest/event_projection.py` | `tests/unit_py/test_ingest_event_projection.py` |
| **A5 — Canonical identity** | `ingest/canonical.py` | `tests/unit_py/test_ingest_canonical.py`, `tests/ingest/test_reftable_pipeline.py` |
| **A6 — Integration** | `ingest/__init__.py`, `pyproject.toml`, `tests/ingest/_paths.py` (add `PYKMC_REFTABLE`), `tests/ingest/conftest.py` if needed | wiring only — no feature module |

**Integration agent (A6) rules:** owns **only** `__init__.py` and `pyproject.toml` plus
the two test-plumbing files. Adds `pyarrow>=14` to the `[ingest]` extra (**pandas 2.0
and scipy are already present; numpy is present; pyarrow is NOT — add it**). Extends
`__init__.py`'s module docstring listing the five new submodules; keeps `__all__ = []`
(nothing imported at package load). No feature agent edits `pyproject.toml` or
`__init__.py`.

**Assembly ownership note:** the harvest/assembly path (`build_class_catalogue`,
backward linking, running all gates, writing Parquet) lives in **A2's** `event_class.py`
and calls A5's `canonical` + A4's `event_projection` lazily. A5 owns the identity math
only; A4 owns event projection only; A2 owns turning many `ProjectedEvent`s into
`EventClass` rows.

---

## 2. `event_class.py` — shared type vocabulary + rate + gates + Parquet (Agent A2)

This module is the schema spine. It defines every value type used across the package,
the rate-space aggregator, the gate functions, the catalogue assembler, and Parquet I/O.
**Module-level intra-package imports: none** (see §0.2).

### 2.1 Integer code enums (single source of truth)

```python
from enum import IntEnum

class Occ(IntEnum):
    EMPTY = 0
    NI = 1
    CR = 2
    FE = 3
    # room for more species 4..253
    OCC_ANY = 254     # grey-mode collapse sentinel (predicate only; never an occupancy value)
    OUTSIDE = 255     # parity-forbidden / out-of-domain / uncovered-by-cluster sentinel

class SaddleKind(IntEnum):
    BRIDGE = 0
    HOLLOW_FCC = 1
    HOLLOW_HCP = 2
    TOP = 3
    OTHER = 4

class DepthKind(IntEnum):
    SURFACE = 0
    SUBSURF = 1
    BULK_OR_DEEPER = 2

class Coloring(IntEnum):
    GREY = 0
    FULL = 1

SYMBOL_TO_OCC: dict[str, Occ]   # {"Ni": Occ.NI, "Cr": Occ.CR, "Fe": Occ.FE, ...} — extend per campaign
OCC_TO_SYMBOL: dict[Occ, str]
```

`type_to_occ(symbol: str) -> Occ` and `occ_to_symbol(o: Occ) -> str` are exported. In
grey mode any occupied species maps to `Occ.OCC_ANY` for identity purposes; `EMPTY` and
`OUTSIDE` are colour-invariant.

### 2.2 Value types (dataclasses, frozen)

```python
Offset = tuple[int, int, int]           # integer FCC lattice offset (i,j,k), even-parity

@dataclass(frozen=True)
class OccPredicate:
    kind: Literal["SPECIES", "EMPTY", "OCC_ANY", "WILDCARD", "OUTSIDE"]
    species: frozenset[Occ] = frozenset()   # populated only for kind=="SPECIES"
    def code(self, coloring: Coloring) -> int: ...   # -> the integer used in the canonical key (§7.3)

@dataclass(frozen=True)
class StencilSite:
    off: Offset
    pred: OccPredicate

@dataclass(frozen=True)
class DeltaSite:
    off: Offset
    before: Occ
    after: Occ

@dataclass(frozen=True)
class PathToken:                        # ONE per mover; §3.3
    start_rank: int                     # canonical rank of the mover's start offset (§4.3) — set during canonicalisation
    kind: SaddleKind                    # categorical topological class of the saddle site
    coord_sig: tuple[int, ...]          # sorted coordination counts of occupied atoms coordinating the saddle site

@dataclass(frozen=True)
class DepthSig:
    kind: DepthKind
    param: int                          # SURFACE: mover start coordination; SUBSURF: d in 1..d_max; BULK_OR_DEEPER: -1
```

### 2.3 `ProjectedEvent` (output of A4, input to A2 assembly + A5 identity)

```python
@dataclass(frozen=True)
class ProjectedEvent:
    anchor0: Offset                     # the initial (frame_e) anchor: the mover's start site; offsets are relative to it
    delta: tuple[DeltaSite, ...]        # occupancy changes (only sites that changed)
    delta_atoms: int                    # #occupied_after - #occupied_before (0 diffusion; <0 dissolution)
    context: tuple[StencilSite, ...]    # V-decorated full r_ctx context (EMPTY included); pred per site
    movers: tuple[Offset, ...]          # start offsets of the true movers (site-change ground truth, §3.2)
    saddle_tokens: tuple[PathToken, ...]# one per mover, in movers-order (start_rank filled later by canonical)
    depth_sig: DepthSig                 # computed operationally from the cluster (§4.1)
    coloring: Coloring
    r_ctx_used: float
    truncated: bool                     # G6: cluster did not cover full r_ctx footprint of every mover
    # --- rate/pairing raw data (per this row) ---
    Ea_fwd_eV: float                    # this row's energy_barrier
    nu0_fwd_hz: float                   # this row's nu0 (HTST) else k_prefactor else NaN
    k_row: float                        # this row's stored k (for G2 cross-check)
    id_saddle: str
    id_final: str
    event_id: str
    idx_ref: int
    idx_backward: int                   # -1 if none
    move_atom_idx: int
    source_row: int                     # positional index into the reference table
    # --- gate provenance ---
    proj_report: "EventProjReport"      # per-event snap residuals / diameter / mover-agreement (§3)
```

### 2.4 Gate types

```python
class GateOutcome(IntEnum):
    PASS = 0
    FAIL = 1
    WARN = 2
    NA   = 3        # gate not applicable (e.g. G2 with no linked pair)

@dataclass(frozen=True)
class GateResult:
    gate: str                           # "G1".."G7"
    outcome: GateOutcome
    detail: str                         # human-readable reason (goes to audit record)
    value: float | None = None          # the measured quantity, when numeric
```

### 2.5 `EventClass` (the catalogue record; superset schema, forward-compatible with Phase B)

Field-for-field per `FINAL_DESIGN.md` §1.3. **Phase A populates** every field marked
`[A]`; fields marked `[F]` are fallback/§6.2-only and are left at their documented empty
default (Phase A never computes them).

*(2026-07-21 amendment — approved `PHASEC_RATE_MODEL_DECISION.md`)* Former `[F]` fields are
re-designated **`[C]` — Phase C rate-model fields** (the §6.2 per-family fallback they served
is retired). They keep their empty defaults until Phase C, so **Phase A/B parquets are
unchanged**; when Phase C first populates them, bump `CATALOGUE_SCHEMA_VERSION` 1 → 2.

```python
@dataclass
class EventClass:
    # --- identity (§4) [A] ---
    class_id: str                       # 64-char blake2b-256 hex of canonical_form — INDEX ONLY
    canonical_form: tuple               # authoritative nested tuple (§7.2)
    canonical_blob: bytes               # TLV encoding of canonical_form (§7.3) — what is hashed; stored in Parquet
    depth_sig: DepthSig
    coloring: Coloring
    move_shape: int                     # u32 species-blind core digest (§4.4) [A]
    family_id: int                      # u32 = move_shape ^ depth_hash (§4.4) — selects fallback regressor [A-computed]
    delta: tuple[DeltaSite, ...]        # canonical orientation (a*, g*)
    delta_atoms: int
    context: tuple[StencilSite, ...]    # canonical orientation
    saddle_token: tuple[PathToken, ...] # ordered by start_rank
    orientation_count: int              # |D4h| / |Stab_D4h(decorated event)| (§4.5) [A]
    r_ctx_used: float
    r_id_used: float                    # == r_ctx_used for Phase A (identity uses full context)
    anchor_pred: OccPredicate           # rarest predicate at the enumeration anchor (§5.2) [A best-effort]
    # --- rate (§6.1) [A] evaluated at t_ref_K ---
    t_ref_K: float
    barriers_eV: tuple[float, ...]      # per member (sorted with members)
    nu0_f_list_hz: tuple[float, ...]
    nu0_b_list_hz: tuple[float, ...]
    dE_pair_list_eV: tuple[float, ...]  # per linked pair; empty if no pairs linked
    k_rate_mean_psinv: float            # nu0.<exp(-Ea/kT)> rate-space mean at t_ref (§6.1)
    Ea_rep_eV: float                    # -kT ln(k_rate_mean / nu0_geo) — reporting-only representative barrier
    nu0_geo_psinv: float                # geometric mean of member nu0 (== nu0_eff for exact reproduction at t_ref)
    Ea_std_eV: float | None             # None for n<3; shrinkage std otherwise
    n_eff: float                        # effective sample count (fallback fit weight; = n members in Phase A)
    Ea_mean_eV: float                   # reporting (arithmetic mean of barriers)
    Ea_median_eV: float                 # reporting
    phi: tuple[float, ...] = ()         # [C] E_sym feature vector, symmetric target Ea−½ΔE (memo §1) — empty until Phase C
    model_version: str | None = None    # [C] E_sym model/tier version
    dE_model_version: str | None = None # [C] H(σ) lattice-energy model version (memo §8-N3/N6) — None until Phase C
    nu0_pair_policy: str | None = None  # [C] "harvested_pair" | "logkra_tier0" (memo §8-N4) — None until Phase C
    # --- pairing (§7.2) [A partial] ---
    backward_class: str | None = None   # class_id of reverse; None if unresolved
    self_reverse: bool = False          # property of canonical form (§7.2)
    dEnergy_eV: float | None = None      # <dE_pair_list> — independent channel; None if no linked pairs
    pair_status: Literal["linked", "synthesized_balanced", "self", "unpaired"] = "unpaired"
    # --- provenance / curation (§8) [A] ---
    source_rows: tuple[int, ...] = ()   # reference-table positional indices contributing
    source_idx_refs: tuple[int, ...] = ()
    source_sim_paths: tuple[str, ...] = ()   # sim path(s) each member came from
    first_seen_cycle: int = 0
    gate_log: tuple[GateResult, ...] = ()
    audit_status: Literal["approved", "pending", "rejected", "quarantined"] = "pending"
    fallback_stats: tuple = ()          # [C] (leverage, hull_flag, model_version, tier) — empty until Phase C
    schema_version: int = CATALOGUE_SCHEMA_VERSION
```

### 2.6 Rate-space aggregation (§6.1) — the exact-lookup path

```python
@dataclass(frozen=True)
class RateAgg:
    k_rate_mean_psinv: float
    Ea_rep_eV: float
    nu0_geo_psinv: float
    Ea_std_eV: float | None
    n_eff: float
    Ea_mean_eV: float
    Ea_median_eV: float
    n_members: int

def aggregate_rate_space(
    barriers_eV: Sequence[float],
    nu0_list_hz: Sequence[float],
    t_ref_K: float,
    *,
    nu0_fallback_hz: float,          # global k0-equivalent in Hz, used when a member nu0 is NaN
    prior_ea_std_floor_eV: float = 0.02,
) -> RateAgg:
    """Rate-space aggregation of repeated measurements of ONE physical class (§6.1).

    Members are paired (Ea_i, nu0_i) and SORTED by (Ea_eV, nu0_hz) before any
    summation, for bit-reproducibility (M4). Missing nu0_i (NaN/<=0) falls back to
    nu0_fallback_hz. The executed rate is the occurrence-weighted mean of member
    rates, converted to ps^-1:

        k_i        = nu0_i[Hz] * exp(-Ea_i / (kB * T))          # s^-1
        k_rate_mean_psinv = mean_i(k_i) / HZ_PER_PSINV
        nu0_geo_psinv     = geomean_i(nu0_i[Hz]) / HZ_PER_PSINV
        Ea_rep_eV         = -kB*T * ln(k_rate_mean_psinv / nu0_geo_psinv)

    NEVER exp(-mean(Ea)) (Jensen error, C1). Ea_std_eV is None for n<3; for n>=3 it is
    sqrt(max(sample_var, prior_ea_std_floor_eV**2)) (never 0 -> never 'maximally
    trustworthy', m1). n_eff = n_members in Phase A.
    """
```

Semantic note: because identity now uses the full `r_ctx` context (§4), every member of
a class is a repeated measurement of the *same* environment, so the rate-space mean is a
legitimate per-class quantity (fixes C1/C4). `Ea_rep_eV`/`nu0_geo_psinv` are chosen so
the single-Arrhenius runtime form `k = nu0_geo * exp(-Ea_rep/kBT)` **reproduces
`k_rate_mean` exactly at `t_ref_K`** (by construction: `nu0_geo·exp(-Ea_rep/kT) ≡
k_rate_mean`) and approximates it within the ±100 K operating window (error is
second-order in `σ_Ea/kT · ΔT/T`). This is the documented approximation.

### 2.7 Gates G1–G7 (§8.2) — see §8 for the precise checks. Public API:

```python
def gate_g1_barrier_bounds(pe, emin_event, emax_event, backward_emin_event) -> GateResult
def gate_g2_detailed_balance(fwd, bwd, t_ref_K, db_tol=0.05) -> GateResult   # NA if no linked pair
def gate_g3_snap_residual(pe, snap_tol=0.9) -> GateResult
def gate_g4_round_trip(pe) -> GateResult                                     # lazy-imports canonical + event_projection
def gate_g5_conservation(pe) -> GateResult
def gate_g6_context_completeness(pe) -> GateResult
def gate_g7_cluster_integrity(pe, rcut) -> GateResult
def run_gates(pe, *, thresholds: "GateThresholds", linked_bwd=None) -> tuple[GateResult, ...]
```

### 2.8 Catalogue assembly + Parquet I/O

```python
def build_class_catalogue(
    events: Sequence[ProjectedEvent],
    *,
    t_ref_K: float,
    thresholds: "GateThresholds",
    nu0_fallback_hz: float,
    first_seen_cycle: int = 0,
) -> list[EventClass]:
    """Group ProjectedEvents by class_id (via canonical.class_id, lazy import), aggregate
    rates (aggregate_rate_space over the class's SORTED members), link backward classes
    (§7.2, via idx_backward/id_saddle), compute dE_pair_list + dEnergy, run all gates,
    set audit_status (approved iff every gate PASS/NA and not first-instance-of-new-class,
    else pending), and return EventClass rows sorted by class_id. Deterministic:
    grouping and all reductions use sorted keys, never dict/set iteration order."""

def catalogue_arrow_schema() -> "pyarrow.Schema": ...          # §9
def write_catalogue_parquet(classes: Sequence[EventClass], path: str | Path) -> None: ...
def read_catalogue_parquet(path: str | Path) -> list[EventClass]: ...
```

`pandas`/`pyarrow` are imported **inside** these three functions only (keeps
`import pylatkmc.ingest.event_class` cheap and dependency-light).

---

## 3. `lattice.py` — FCC embedding + D₄ₕ group (Agent A1)

Pure integer/`numpy` geometry. No pandas, no identity logic, no rates.

### 3.1 D₄ₕ group — pinned representation (16 integer 3×3 matrices)

The (100)-slab point group is **D₄ₕ, order 16** (§1.1): the subgroup of Oₕ that fixes
the z-axis up to sign. Represent it as the **8 signed xy-permutations × 2 z-signs**.

```python
IntMat3 = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]

def _build_d4h() -> tuple[IntMat3, ...]:
    """The 16 D4h ops as integer 3x3 signed-permutation matrices, generated
    programmatically in a fixed order. Block form: a 2x2 signed xy-permutation
    (the 8 symmetries of the square) direct-product z -> +/- z."""
    xy: list[list[list[int]]] = []
    for (px, py) in ((0, 1), (1, 0)):          # x-row -> col px ; y-row -> col py
        for sx in (1, -1):
            for sy in (1, -1):
                m = [[0, 0], [0, 0]]
                m[0][px] = sx
                m[1][py] = sy
                xy.append(m)                    # 8 signed 2x2 perms
    ops: list[IntMat3] = []
    for m2 in xy:
        for sz in (1, -1):
            ops.append(((m2[0][0], m2[0][1], 0),
                        (m2[1][0], m2[1][1], 0),
                        (0, 0, sz)))            # 8 * 2 = 16
    return tuple(ops)

D4H_OPS: tuple[IntMat3, ...] = _build_d4h()     # frozen module constant; index 0..15 is the canonical op order

# CLOSURE ASSERTION at import (required — this is the group-validity guarantee):
#   _S = set(D4H_OPS)
#   assert len(_S) == 16
#   assert all(matmul3(A, B) in _S for A in D4H_OPS for B in D4H_OPS)  # closed
#   assert all(matmul3(A, INVERSE_of_A) == IDENTITY ...)              # inverses present (implied by closure+finiteness)
```

```python
@dataclass(frozen=True)
class SymOp:
    index: int          # 0..15, position in D4H_OPS (the stable tie-break key)
    mat: IntMat3

D4H: tuple[SymOp, ...]                       # SymOp wrappers, index-ordered

def matmul3(A: IntMat3, B: IntMat3) -> IntMat3: ...
def apply_op(op: SymOp | IntMat3, v: Offset) -> Offset: ...   # integer matrix @ vector
def compose(a: SymOp, b: SymOp) -> SymOp: ...
def op_inverse(a: SymOp) -> SymOp: ...
```

Guarantees the closure assertion pins: |group| == 16, closed under `matmul3`, each op is
a signed permutation (one ±1 per row/col), each **preserves even parity**
(`sum(apply_op(g, v)) % 2 == sum(v) % 2`) and **fixes z up to sign**
(`mat[2] == (0,0,±1)` and `mat[0][2]==mat[1][2]==0`).

### 3.2 FCC embedding

```python
def is_even_parity(off: Offset) -> bool                 # (i+j+k) % 2 == 0
NN12_OFFSETS: tuple[Offset, ...]    # 12 perms/signs of (±1,±1,0)   1NN
NN2_OFFSETS:  tuple[Offset, ...]    # 6  perms of (±2,0,0)          2NN
NN3_OFFSETS:  tuple[Offset, ...]    # 24 perms/signs of (±2,±1,±1)  3NN
def shell_offsets(shell: int) -> tuple[Offset, ...]     # 1|2|3
def cartesian(off: Offset, origin: np.ndarray, h: float) -> np.ndarray   # origin + h*(i,j,k)
def round_to_even_parity(u: np.ndarray) -> Offset:
    """Nearest even-parity site: round u; if parity is odd, flip the coordinate with the
    largest rounding error (the FCC Voronoi cell is the rhombic dodecahedron)."""
def second_nearest_even_parity(u: np.ndarray) -> Offset: ...   # runner-up (hysteresis test, §2.2)
def coordination(occ_of: Callable[[Offset], Occ], site: Offset) -> int:
    """count of occupied entries among the 12-star (also the dealloying eligibility test)."""
```

Semantic note (§1.1): a bulk atom's 12 NN split 4 in-layer + 4 to k+1 + 4 to k−1; a
(100) surface atom keeps 4 in-layer + 4 below = coordination 8. Neighbour access is
pure integer table lookup.

---

## 4. `projection.py` — forward configuration projection §2 (Agent A3)

Maps a relaxed off-lattice full-cell snapshot to occupancy on the FCC frame,
deterministically, reporting anything unmappable. Independent of the identity pipeline
(`event_projection` does its *own* local fit); used for round-trip determinism tests and
seeding.

### 4.1 Types

```python
@dataclass(frozen=True)
class LatticeFrame:                 # calibrated ONCE per campaign (§2.1)
    a: float
    h: float
    origin: tuple[float, float, float]
    R_campaign: tuple[tuple[float, ...], ...]     # 3x3; asserted ||R - I|| < rot_tol
    n_i: int
    n_j: int
    k_range: tuple[int, int]
    layer_z: tuple[float, ...]      # detected z of each layer (absorbs surface relaxation) — USED in the snap
    strain: tuple[float, float, float]
    k_top: int
    k_bot: int
    seeds: tuple[int, int]          # (ransac_seed, neldermead_seed) — recorded for reproducibility
    content_hash: str               # blake2b hex of the calibrated frame

Occupancy = dict[Offset, Occ]       # sparse; ingest representation (NOT the runtime SoA Grid — out of scope)

@dataclass(frozen=True)
class ProjectionReport:
    max_residual: float
    residual_histogram: tuple[tuple[float, int], ...]
    n_unmappable: int
    n_collision: int
    n_ambiguous: int
    stall_streak: int
    verdict: Literal["accept", "accept_warn", "handback_pyKMC", "unprojectable"]

@dataclass(frozen=True)
class EventProjReport:              # per-event residual detail (carried on ProjectedEvent)
    max_residual: float
    mover_max_residual: float
    diameter: float
    mover_agreement: bool           # move_atom_idx in detected movers (G4)
```

### 4.2 Functions

```python
def calibrate_frame(X0, types0, cell0, *, a_nominal=A_NOMINAL, seeds) -> LatticeFrame:
    """ONCE at campaign start (§2.1). Assert diagonal (orthorhombic) cell; a from PBC cell
    (|a_x - a_y| > 1% -> abort/audit FRAME_TILT); guarded KDE layer detection; seeded
    Kabsch/RANSAC to ideal FCC; assert ||R - I|| < rot_tol else audit(FRAME_TILT).
    RANSAC/Nelder-Mead run ONLY here, seeded, recorded in frame.seeds."""

def register_cycle(X, types, cell, frame) -> LatticeFrame:
    """EACH cycle, deterministic (no RNG): align snapshot into frame axes (Xa = R^T X, so
    R == I in the working frame), bounded rigid-translation drift only (closed form),
    uniform thermal strain from the PBC cell; assert ||d_origin|| < drift_tol else
    audit(FRAME_DRIFT). Returns frame with updated origin/h."""

def project(X, types, frame, prev_occ: Occupancy | None = None) -> tuple[Occupancy, ProjectionReport]:
    """Snap atoms to sites (§2.2): layer-aware residual scored against frame.layer_z[k];
    hysteresis band snap_hysteresis=0.3 A guards the parity-Voronoi face -> ambiguous atoms
    inherit prev_occ or route to audit (deterministic under thermal jitter); collisions are
    a HARD structural signal -> hand back to pyKMC (never silently drop). Build is_vacuum
    (flood-fill) + depth (BFS). Assert I4 conservation:
    count(occ != EMPTY) == len(X) - n_unmappable - n_collision."""

def flood_fill_vacuum(occ: Occupancy, frame) -> set[Offset]:
    """O(N) BFS from the +/-z margin EMPTY sites through EMPTY neighbours (§1.3, Geom-6).
    An EMPTY site with >=1 occupied neighbour and NOT vacuum is a vacancy/adatom-target."""

def depth_bfs(occ, is_vacuum, frame, d_max: int) -> dict[Offset, int]:
    """min layers to the vacuum front, capped at d_max then BULK_OR_DEEPER."""

def to_atomistic(occ: Occupancy, frame) -> tuple[list[tuple[str, tuple[float, float, float]]], str]:
    """Deterministic reverse map (§7.3): emit atoms at IDEAL axis-aligned positions
    origin + h*(i,j,k) (R == I) in sorted site order; EMPTY/OUTSIDE emit nothing; return
    (atoms, blake2b content hash). Enables the project->reverse->reproject round-trip test.
    NOTE: the runtime grid-level reverse map is out of Phase A scope; this is the minimal
    ingest form."""
```

Tolerances (module constants, §2.3): `SNAP_TOL = 0.9`, `SOFT_SURFACE_TOL = 1.05`,
`SNAP_HYSTERESIS = 0.3`, `N_SOFT = 3` (all Å where applicable). Cycle-policy verdict per
the §2.3 table; `unprojectable` hands the rough snapshot back to pyKMC and marks
`PROJECTION_STALLED` (never re-emit a stale grid — Geom-5).

---

## 5. `event_projection.py` — event projection §3 (Agent A4)

Turns one pyKMC reference row into a `ProjectedEvent`. Does its **own** local FCC fit
(does not use `projection.LatticeFrame`).

```python
def min_image_unwrap(positions: np.ndarray, about: int, cell: np.ndarray) -> np.ndarray:
    """Unwrap a raw-wrapped subset cluster about its `about` atom using the event's own
    PBC cell (Geom-1). MUST run first, before any fit. A mover within ~rcut of an in-plane
    face has -x/-y neighbours wrapped to the far box side; without this, fit_local_fcc
    infers a PHANTOM in-plane surface (routes a bulk hop into the surface regime)."""

def fit_local_fcc(P0: np.ndarray, seed_idx: int) -> "LocalFrame":
    """Procrustes of nn bond directions -> ideal <110>; h from mean bond length (§3.1)."""

def detect_movers(P0, P2, frame_e) -> tuple[tuple[Offset, ...], list[Offset]]:
    """SITE-CHANGE is ground truth (§3.2): movers = {p : snap(P0[p]) != snap(P2[p])}.
    Displacement thresholds are only a pre-filter. Catches concerted events move_atom_idx
    names only one of."""

def classify_saddle_site(psad: np.ndarray, S0, S2, prev_kind: SaddleKind | None) -> SaddleKind:
    """CATEGORICAL (§3.3, Geom-7/M1): kind from COUNTING occupied atoms coordinating the
    transition-state position (bridge=2, FCC/HCP hollow=3, top=1) with a robust geometric
    test + a hysteresis band (a saddle within eps of a bridge/hollow boundary keeps its
    previously-assigned kind). NOT a rounded continuous displacement. The real-valued
    saddle offset is kept in provenance, never in identity."""

def compute_depth_sig(context: Sequence[StencilSite], movers, S0) -> DepthSig:
    """Operational depth signature (§4.1), IDENTICALLY defined at ingest and runtime:
      - decorated r_ctx reaches a contiguous EMPTY hemisphere with occupied backing
        -> SURFACE(coordination of mover start site)
      - else d = min layers from mover to nearest EMPTY-with-occupied-neighbour in cluster;
        d <= d_max -> SUBSURF(d) ; else BULK_OR_DEEPER (explicit merge).
    d_max = floor(rcut / (a/2)) - 1."""

def project_event(row: "pd.Series | Mapping", *, coloring: Coloring, rcut: float,
                  d_max: int, r_ctx_min: float) -> ProjectedEvent:
    """Full §3 pipeline: unwrap (all of initial/final/saddle about move_atom_idx) ->
    diameter assert (< 2*rcut, gate G7) -> fit_local_fcc -> detect true movers
    (assert move_atom_idx in movers else flag MOVER_DISAGREEMENT, gate G4) -> build delta,
    delta_atoms, V-decorated context to r_ctx = max(1st+2nd shells, rcut, (d_surf+1)*(a/2))
    -> saddle tokens (one per mover) -> depth_sig. start_rank on tokens is filled by
    canonical (left 0 here). truncated per G6. Returns ProjectedEvent."""
```

Context rule (§3.3, C3): `context` includes **every ideal lattice site within `r_ctx` of
the moved-sites centroid**, each with `pred = species_pred(occ_before(site))`
(EMPTY included, so the surface stabiliser and vacancy arrangement fall out of the
decoration). A site inside the footprint the cluster does not cover → `pred` kind
`OUTSIDE` and `truncated=True`.

---

## 6. `canonical.py` — class identity §4 (Agent A5)

The heart. Produces the **complete orbit invariant** under (translation × D₄ₕ × internal
automorphism), minimised jointly over anchor × group.

```python
def candidate_anchors(pe: ProjectedEvent) -> list[Offset]:
    """Every MOVED site is a candidate anchor (§4.2). Reference semantics: return all of
    pe.movers. NO lex(offset) tie-break may enter identity (offsets are frame-dependent).
    Optional G-invariant pruning by (occ_priority(before(m)), round(|cart(m)-centroid|,1e-3))
    is permitted ONLY if it provably does not change the min — the reference is full
    enumeration over all moved sites."""

def canonical_rank_map(movers, anchor: Offset, g: SymOp) -> dict[Offset, int]:
    """Deterministic mover order in THIS (anchor, g): key(m) = apply_op(g, sub(m, anchor));
    rank = position after lexicographic sort of keys. Movers are distinct sites so keys are
    distinct (g is a bijection) -> no ties."""

def serialize_variant(pe, anchor: Offset, g: SymOp) -> tuple:
    """Re-express everything relative to `anchor`, rotate by `g`, and build the comparable
    integer tuple (§7.1). Returns (depth_kind, depth_param, delta_seq, context_seq,
    saddle_seq) — all nested tuples of ints, totally ordered by Python tuple comparison."""

def canonical_form(pe: ProjectedEvent) -> tuple:
    """min over (anchor in candidate_anchors) x (g in D4H) of serialize_variant, then
    prepend the (anchor,g)-invariant prefix. Returns the AUTHORITATIVE nested tuple (§7.2)."""

def canonical_blob(cf: tuple) -> bytes            # TLV encoding (§7.3)
def class_id(pe_or_cf) -> str                     # blake2b(canonical_blob, digest_size=32).hexdigest()
def argmin_orientation(pe) -> tuple[Offset, SymOp] # (a*, g*): first (anchor,g) achieving the min (fixed iteration order)
def orientation_count(pe) -> int                  # |D4h| / |Stab|; = #distinct images of the decorated stencil under D4H (§4.5)
def is_self_reverse(pe) -> bool                   # exists g in D4h mapping (delta+context+ordered token) with before<->after swapped onto itself (§7.2, Sym-5)
def move_shape(pe) -> int                         # u32: blake2b-4 of the grey (species-blind) core canonical sub-tuple (§4.4)
def depth_hash(ds: DepthSig) -> int               # u32 from (kind, param)
def family_id(pe) -> int                          # u32 = move_shape ^ depth_hash
```

Semantic notes:
- **Completeness (Sym-2).** Minimising over anchor **and** group is the genuine orbit
  invariant: two harvest orientations of a symmetric event (e.g. a divacancy concerted
  move where the two EMPTY movers tie) land on the **same** `class_id`. The draft's
  group-only minimisation about a single frame-dependent anchor split them — the root of
  Sym-2. Equal canonical form ⟺ same class.
- **Saddle token in the canonical frame (Geom-7).** `start_rank` is assigned in the
  winning `(a*, g*)`; `kind`/`coord_sig` are frame-invariant. The token tuple is ordered
  by `start_rank`, binding each mover's start/end/saddle together (Sym-6) so a `g` that
  pairs mover-1's start with mover-2's saddle cannot produce a spurious match.
- **Full context always (C3, §4.4).** Identity uses the full `r_ctx` context — no
  barrier-driven promotion, no `SPLIT_CHECK`. Novelty is "a full-`r_ctx` context never
  seen," independent of barrier agreement.
- **Grey vs full (§4.3).** `coloring` is part of the key so a catalogue is never silently
  mixed. Grey collapses every occupied `Occ` to `OCC_ANY` *before* serialization; `EMPTY`
  and `OUTSIDE` are colour-invariant.

---

## 7. Canonical-form serialization — byte-exact (normative; two implementers must match)

This section is the contract's most load-bearing part. Any two conforming
implementations MUST produce identical `class_id` for the same `ProjectedEvent`.

### 7.1 Per-`(anchor, g)` variant tuple

For a chosen `anchor a` and `g ∈ D4H` (with `sub(x,a) = (x[0]-a[0], x[1]-a[1],
x[2]-a[2])` and `T(x) = apply_op(g, sub(x, a))`):

```
delta_seq   = sorted(
                (T(ds.off)[0], T(ds.off)[1], T(ds.off)[2],
                 _occ_code(ds.before, coloring), _occ_code(ds.after, coloring))
                for ds in pe.delta )
context_seq = sorted(
                (T(cs.off)[0], T(cs.off)[1], T(cs.off)[2], cs.pred.code(coloring))
                for cs in pe.context )
ranks       = canonical_rank_map(pe.movers, a, g)          # mover -> int
saddle_seq  = tuple(                                        # ordered by start_rank ascending
                (ranks[m], int(tok.kind), tuple(int(c) for c in tok.coord_sig))
                for m, tok in _movers_with_tokens(pe) sorted by ranks[m] )
depth_kind  = int(pe.depth_sig.kind)
depth_param = int(pe.depth_sig.param)
variant     = (depth_kind, depth_param, delta_seq, context_seq, saddle_seq)
```

- `sorted(...)` uses ordinary Python tuple order over integers (total order; no floats).
- `_occ_code(o, coloring)`: `EMPTY→0`, `OUTSIDE→255`; in FULL colour an occupied species →
  its `Occ` int (1,2,3,…); in GREY any occupied species → `254` (`OCC_ANY`).
- `OccPredicate.code(coloring)`: `EMPTY→0`, `OUTSIDE→255`, `WILDCARD→253`; SPECIES → in
  FULL the single species int (predicates are single-species at ingest), in GREY → `254`.

### 7.2 Authoritative `canonical_form` tuple

```
best = min(serialize_variant(pe, a, g) for a in candidate_anchors(pe) for g in D4H)  # (depth_kind, depth_param, delta_seq, context_seq, saddle_seq)
canonical_form = (
    CANON_SCHEMA_VERSION,      # int, currently 1
    int(pe.coloring),          # 0 grey, 1 full
    int(pe.delta_atoms),
    best[0],                   # depth_kind
    best[1],                   # depth_param
    best[2],                   # delta_seq
    best[3],                   # context_seq
    best[4],                   # saddle_seq
)
```

The `(version, coloring, delta_atoms)` prefix is `(a,g)`-invariant and prepended after the
argmin; `depth_kind/param` are also `(a,g)`-invariant (property of the physical event) so
they never affect the argmin but are stored. This tuple is **authoritative and
tolerance-free**; the digest is an index.

### 7.3 TLV byte encoding → `class_id`

`canonical_blob` is a self-delimiting tag-length-value walk of `canonical_form`
(verified injective):

```
INT_TAG = b"\x01"   # followed by 8-byte big-endian two's-complement:  struct.pack(">q", v)
SEQ_TAG = b"\x02"   # followed by 4-byte big-endian unsigned length:  struct.pack(">I", n), then n encoded elements

encode(int v)            -> INT_TAG + struct.pack(">q", int(v))
encode(tuple/list x)     -> SEQ_TAG + struct.pack(">I", len(x)) + b"".join(encode(e) for e in x)

canonical_blob = encode(canonical_form)
class_id       = hashlib.blake2b(canonical_blob, digest_size=32).hexdigest()   # 64 hex chars
```

Every integer occupies exactly 9 bytes; every sequence a 5-byte header + its children.
Distinct nested structures always produce distinct bytes, so no structural collision is
possible. `canonical_blob` is stored in Parquet (binary) as the reconstructable
authoritative form; `class_id` is the index.

### 7.4 `move_shape` / `family_id` (u32; consumer is §6.2, out of Phase A scope)

```
grey_core   = the (delta restricted to moved sites + their occupied 1st-shell) as a
              GREY, species-blind sub-event; canonicalise it via §7.1/7.2 with
              coloring=GREY, context restricted to the 1st shell of moved sites.
move_shape  = int.from_bytes(blake2b(encode(grey_core_form), digest_size=4), "big")   # u32
depth_hash  = ((int(kind) & 0xFFFF) << 16) | (int(param) & 0xFFFF)                     # u32
family_id   = move_shape ^ depth_hash                                                  # u32
```

Computed deterministically; the regressor that consumes `family_id` is not built in
Phase A.

---

## 8. Gates G1–G7 — ingest-applicable subset (§8.2)

**Decision:** all seven gates apply at ingest; **G2 is conditional** on a linked
forward/backward pair (returns `NA` otherwise). Auto-admit (`audit_status="approved"`)
iff every applicable gate is `PASS`/`NA` **and** the class is not a first-instance
new class; any `FAIL` or first-instance routes to `pending` (audit queue).

```python
@dataclass(frozen=True)
class GateThresholds:
    emin_event: float
    emax_event: float
    backward_emin_event: float
    snap_tol: float = 0.9
    db_tol: float = 0.05          # ln-rate units
    rcut: float = ...             # from pyKMC config
```

| Gate | Check (Phase A) | Threshold | Outcome semantics |
|---|---|---|---|
| **G1** barrier bounds | `emin_event ≤ Ea_fwd ≤ emax_event` and `Ea_bwd ≥ emin_event` (Ea_bwd only if linked) | reuse pyKMC fields | FAIL out-of-bounds |
| **G2** detailed balance (REAL, C2) | linked pair only: per-member `dE_pair` spread `< db_tol`; **and** `|ln(k_f/k_b) − (ln(ν0_f/ν0_b) − ⟨dE_pair⟩/kT)| < db_tol` using the **independent** ⟨dE_pair⟩ from linked rows; **and** agreement with pyKMC's stored per-row `k` | `db_tol=0.05` | **NA** if no linked pair; FAIL is a genuine failure (not a tautology) |
| **G3** snap residual | every cluster atom snaps `< snap_tol`; movers strictly `< snap_tol`; saddle exempt | `snap_tol=0.9 Å` | FAIL keeps off-lattice events out |
| **G4** round-trip | re-expand projected event to ideal positions → re-`project_event` → identical `class_id`; **and** `move_atom_idx ∈ movers` | exact id; boolean | FAIL catches mis-projection + concerted mislabel |
| **G5** conservation (v1) | before/after species multiset equal (atom-conserving, `delta_atoms==0`); projection-time I4 held | multiset equality | FAIL surfaces non-conservative events (the switch dissolution later flips) |
| **G6** context completeness | cluster covers the full `r_ctx` footprint of every moved site | `pe.truncated == False` | WARN + `truncated` flag + larger-`rcut` re-harvest note |
| **G7** cluster integrity | min-image-unwrapped diameter `< 2·rcut`; no projection collision | `< 2·rcut` | FAIL → audit(STRADDLING_CLUSTER/COLLISION) |

Audit reasons (recorded in `GateResult.detail` / catalogue provenance) use the §8.3
vocabulary: `NEW_CLASS, GATE_FAIL, OUTLIER_BARRIER, UNMAPPABLE, COLLISION,
STRADDLING_CLUSTER, PAIR_CLOSURE, MOVER_MISMATCH, TRUNCATED, CONTEXT_UNDERRESOLVED,
PROJECTION_STALLED, FRAME_DRIFT`.

**Backward pairing (§7.2), Phase A extent.** For linked pairs (`idx_backward` present,
shared `id_saddle`): set `backward_class`, `pair_status="linked"`, compute
`dE_pair = Ea_fwd − Ea_bwd = E_min2 − E_min1` per member, `dEnergy = mean(dE_pair_list)`
(an **independent** channel from barriers, enabling a real G2). `is_self_reverse` sets
`pair_status="self"`. The `synthesized_balanced` reverse (one-sided harvest) is
**specified but optional in Phase A**: if generated, emit it flagged `pending` with
`k_b = k_f·(ν0_b/ν0_f)·exp(ΔE/kT)` and reason `PAIR_CLOSURE`; otherwise leave
`pair_status="unpaired"` and enqueue `PAIR_CLOSURE`. Do **not** force `dEnergy=0` for
context-asymmetric hops.

---

## 9. `EventClass` Parquet catalogue schema (§14)

One Parquet file keyed by `class_id`; the **tuple (`canonical_blob`) is authoritative**,
the digest is the index. pyarrow schema (`catalogue_arrow_schema()`), column order fixed:

```
class_id             : string            (64-char blake2b-256 hex)      # index
canonical_blob       : binary            (TLV bytes, §7.3)              # authoritative
schema_version       : int32
coloring             : string            ("grey" | "full")
depth_sig_kind       : string            ("SURFACE" | "SUBSURF" | "BULK_OR_DEEPER")
depth_sig_param      : int32
move_shape           : int64             (u32 stored widened)
family_id            : int64             (u32 stored widened)
delta_atoms          : int32
orientation_count    : int32
r_ctx_used           : float64
r_id_used            : float64
anchor_pred          : string            (repr of the rarest predicate)
delta                : list<struct{dx:int32, dy:int32, dz:int32, before:int8, after:int8}>
context              : list<struct{dx:int32, dy:int32, dz:int32, pred:int16}>
saddle_token         : list<struct{start_rank:int32, kind:string, coord_sig:list<int32>}>
# --- rate (at t_ref) ---
t_ref_K              : float64
barriers_eV          : list<float64>
nu0_f_list_hz        : list<float64>
nu0_b_list_hz        : list<float64>
dE_pair_list_eV      : list<float64>
k_rate_mean_psinv    : float64
Ea_rep_eV            : float64
nu0_geo_psinv        : float64
Ea_std_eV            : float64           (nullable — null for n<3)
n_eff                : float64
Ea_mean_eV           : float64
Ea_median_eV         : float64
# --- pairing ---
backward_class       : string            (nullable)
self_reverse         : bool
dEnergy_eV           : float64           (nullable)
pair_status          : string            ("linked"|"synthesized_balanced"|"self"|"unpaired")
# --- provenance / curation ---
source_rows          : list<int64>
source_idx_refs      : list<int64>
source_sim_paths     : list<string>
first_seen_cycle     : int32
audit_status         : string            ("approved"|"pending"|"rejected"|"quarantined")
gate_log             : list<struct{gate:string, outcome:int8, detail:string, value:float64}>   # value nullable
```

Rows are written **sorted by `class_id`** (determinism). `phi`, `model_version`,
`fallback_stats` are §6.2-only and omitted from the Phase A Parquet (the dataclass keeps
them at empty defaults for Phase B forward-compat). `read_catalogue_parquet` round-trips
every present column back into `EventClass`.

---

## 10. `build_family_rate_table.py` — §6.1 rate-space edit (Agent A2)

Keep the existing `FAMILY_REGISTRY`-driven grouping and file layout; **replace the
barrier aggregation** and add columns. `_barrier_stats` gains rate-space outputs by
delegating to `event_class.aggregate_rate_space`.

- **New CLI arg:** `--t-ref` (float K, **required**, no default — force the caller to
  state it; the campaign uses 500 K). Stamp it into the table (`T_ref_K` column) and the
  console summary.
- **Per (family_id, family_bucket_id) group**, compute over the accepted rows'
  `energy_barrier` + resolved `nu0_Hz` (existing `attach_nu0` precedence: per-bucket →
  per-family → k0):

  | New column | Definition |
  |---|---|
  | `k_rate_mean_psinv` | `mean_i(nu0_i[Hz]·exp(−Ea_i/kT_ref)) / 1e12` over the **sorted** member list |
  | `Ea_rep_eV` | `−kB·T_ref·ln(k_rate_mean_psinv / nu0_geo_psinv)` (rate-equivalent barrier, reporting) |
  | `nu0_geo_psinv` | `geomean_i(nu0_i[Hz]) / 1e12` (== `nu0_eff`: the runtime prefactor that reproduces the mean exactly at `T_ref`) |
  | `T_ref_K` | the stamped reference temperature |

- **Keep** `Ea_mean_eV`, `Ea_median_eV`, `Ea_min_eV`, `Ea_max_eV`, `Ea_std_eV`,
  `n_events` as **reporting-only** columns (do not delete — downstream reviewers rely on
  them). The runtime path should consume `nu0_geo_psinv` + `Ea_rep_eV`, not `Ea_mean_eV`.
- **Empty/visible-only rows** keep NaN for the rate-space columns (as they already do for
  `Ea_mean_eV`).
- **Document** in the module docstring: rate-space aggregation is Jensen-exact
  (`⟨exp(−Ea/kT)⟩`, not `exp(−⟨Ea⟩)`); `nu0_geo`/`Ea_rep` reproduce `k_rate_mean` at
  `T_ref` exactly and approximate it within ±100 K; **units are ps⁻¹** (Hz÷1e12).

This is the "immediate independent win" of `COMPARISON.md` §4 Phase A.1 — correct even
while the old family scheme is still the identity layer.

---

## 11. Test plan — file by file (§12)

Pure-math tests go in `tests/unit_py/` (the only CI suite) with
`pytest.importorskip("pyarrow")` / `importorskip("pandas")` guards on the
ingest-only-dep tests so a bare CI run stays green without `[ingest]`. Data-dependent
tests go in `tests/ingest/` behind `PYKMC_REFTABLE` (see §11.6). Every test asserts the
specific property named.

### 11.1 `tests/unit_py/test_ingest_lattice.py` (A1)
- **Group closure/order 16:** `len(set(D4H_OPS)) == 16`; closed under `matmul3`; every op
  is a signed permutation; inverses present.
- **Parity preservation:** for 1000 random even-parity offsets and all 16 ops,
  `sum(apply_op(g,v)) % 2 == 0`.
- **z-fixed-up-to-sign:** every op has `mat[2] == (0,0,±1)`, `mat[0][2]==mat[1][2]==0`.
- **Shells:** 12 (2.489 Å), 6 (3.520 Å), 24 (4.311 Å) NN offsets; (100) layering
  4-in-layer + 8-cross-layer bulk, 8 at surface.
- **`round_to_even_parity`:** exact nearest FCC site; a planted parity-Voronoi-face point
  reports its two nearest sites via `second_nearest_even_parity`.

### 11.2 `tests/unit_py/test_ingest_canonical.py` (A5)
- **Canonical invariance:** property test — for random `g∈D4H`, random integer
  translations, and random anchor/atom-order shuffles of a synthetic `ProjectedEvent`,
  `class_id(transform(e)) == class_id(e)`.
- **Distinctness:** bulk in-plane vs inter-layer ⟨110⟩ hop → **distinct** class_ids;
  two genuinely different decorated events → different keys; a Ni-hop-near-Cr vs pure-Ni
  hop (full colour) → different keys, but **same** key in grey mode.
- **Symmetric multi-anchor:** a divacancy concerted event built in two orientations →
  **one** `class_id` (min over anchor×group).
- **σ_h coverage:** a top-surface event's σ_h image → same `class_id` as its
  bottom-surface counterpart.
- **depth_sig splitting:** identical stencils with SURFACE/SUBSURF/BULK depth_sig →
  distinct keys.
- **Byte-exactness:** `canonical_blob` matches a hand-encoded TLV golden for a tiny fixed
  event; `class_id` is the blake2b-256 hex of that blob.
- **orientation_count:** `== |D4h|/|stabiliser|` verified by brute force on a few events.
- **move_shape/family_id:** deterministic across `PYTHONHASHSEED` (two subprocess seeds).

### 11.3 `tests/unit_py/test_ingest_event_projection.py` (A4)
- **Boundary unwrap (Geom-1):** an event with its mover 1.5 Å from an in-plane face →
  `min_image_unwrap` restores 2.49 Å neighbours; regime = BULK (not surface); G7 passes;
  the **same event without unwrap** would misclassify (regression guard).
- **True movers (§3.2):** a synthetic concerted event where `move_atom_idx` names one of
  three movers → `detect_movers` returns all three; G4 mover-agreement holds.
- **Saddle token stability (Geom-7/M1):** over-bridge vs through-hollow → distinct `kind`;
  a token is **stable across 100 re-relaxations** (jitter) of the same event (no flicker);
  a 2-mover event's two chiral variants stay distinct (ordered, mover-bound).
- **depth_sig operational:** SURFACE/SUBSURF/BULK_OR_DEEPER from planted clusters; capped
  at `d_max`.

### 11.4 `tests/unit_py/test_ingest_projection.py` (A3)
- **Jitter determinism (Geom-2):** perturb a synthetic slab by `N(0, 0.05 Å)` **100×** →
  the occupancy grid is **invariant** (hysteresis); a planted parity-Voronoi-face atom
  routes to audit, not a coin-flip snap.
- **Conservation (Geom-8):** a planted split-interstitial → **collision → hand-back**,
  not accept; I4 fires if an atom would be dropped.
- **Flood-fill (Geom-6):** a slab with a planted overhang + buried pore → correct
  vacancy/vacuum labels; `depth_bfs` capped at `d_max`.
- **Round-trip (Geom-4):** `project → to_atomistic (R≡I) → project` → identical occupancy;
  byte-stable content hash; the `x=0` face coincides with the image of `x=Lx`.
- **Frame calibration (Geom-10):** calibrate twice with the same seeds → **byte-identical**
  `content_hash`; a `‖R−I‖ > rot_tol` slab aborts to audit.

### 11.5 `tests/unit_py/test_ingest_rate_agg.py` + `test_ingest_parquet.py` (A2, importorskip)
- **Rate-space vs hand-computed (C1):** `aggregate_rate_space` on a hand-built 3-member
  set matches a brute-force `mean(nu0·exp(−Ea/kT))/1e12`; `exp(−mean(Ea))` differs by the
  predicted **Jensen factor** (assert the ~6× gap on a 0.05 eV spread at 300 K).
- **Reproduction at T_ref:** `nu0_geo_psinv·exp(−Ea_rep/kB·T_ref) == k_rate_mean_psinv`
  to float tolerance.
- **Ea_std/n_eff:** `Ea_std_eV is None` for n<3; prior floor applied for n≥3; `n_eff == n`.
- **Sorted determinism (M4):** shuffling the member input order yields identical outputs.
- **Parquet round-trip:** `write_catalogue_parquet → read_catalogue_parquet` reproduces
  every field incl. nested `delta`/`context`/`saddle_token`/`gate_log`; `canonical_blob`
  decodes back to `canonical_form`; rows are class_id-sorted.
- **Gates:** G2 **passes** on a constructed linked pair (correct ν0_f/ν0_b + independent
  ⟨dE_pair⟩) and **fails** on a fold-in of unpaired fwd/bwd members (proves it is not a
  tautology, C2); G2 is `NA` with no linked pair; G1/G3/G5/G7 fire on planted violations;
  G4 fails on a mis-projected event; **Jensen direction check** `exp(−⟨Ea⟩) ≤ ⟨exp(−Ea)⟩`.

### 11.6 `tests/ingest/test_rate_space_table.py` (A2) + `test_reftable_pipeline.py` (A5)
Behind `PYKMC_REFTABLE` (integration agent adds resolution to `tests/ingest/_paths.py`):
default to the two real pickles when the env var is unset —
`/home/kerr/pykmc/scratch_nicr_htst/reference_table.pickle` and
`/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac/reference_table.pickle` — and
**skip** (never fail) if neither is present.
- `test_rate_space_table.py`: run `build_family_rate_table` on a real classified CSV;
  assert the new columns exist, are ps⁻¹-scaled, reproduce `k_rate_mean` at `T_ref`, and
  that `Ea_rep ≥ Ea_min` and `k_rate_mean ≥ exp(−Ea_mean)`-equivalent (rate-space ≥
  mean-then-exp).
- `test_reftable_pipeline.py`: load a reference table, `project_event` a handful of rows,
  canonicalise, `build_class_catalogue`, write+read Parquet; assert no crash, all
  `class_id`s are 64-hex, `orientation_count ≥ 1`, linked pairs get `dEnergy_eV`, and the
  **on-lattice partition refines the `id_saddle` partition** in rate units (two rows with
  different `id_saddle` share a `κ` only if `|ΔEa| < k_BT`, else flagged
  `CONTEXT_UNDERRESOLVED`).

### 11.7 Integration agent (A6)
- Confirm `pip install -e ".[ingest]"` pulls `pyarrow`; `import pylatkmc.ingest` stays
  cheap (no pandas/pyarrow at package load — assert via a subprocess import timing/oracle
  or by asserting the submodules are not imported).
- `pytest tests/unit_py/ -q` green **without** `[ingest]` (importorskip guards work).

---

## 12. Open questions resolved (with design citations)

1. **How does T enter the T-independent catalogue?** (task-flagged.)
   *Resolution:* the catalogue stores T-independent authoritative data (`barriers_eV`,
   `nu0_*_list_hz`) **plus** a stamped `t_ref_K` and the three T-derived columns
   (`k_rate_mean_psinv`, `Ea_rep_eV`, `nu0_geo_psinv`) computed at `t_ref`. `T_ref` is an
   **explicit required argument** to both `aggregate_rate_space` and
   `build_family_rate_table --t-ref`. The runtime evaluates `k = nu0_geo·exp(−Ea_rep/kBT)`
   at any T; at `T_ref` it reproduces `k_rate_mean` **exactly** (algebraic identity),
   nearby it is a documented second-order approximation. Cite §6.1 (`Ea_rep = −kT·ln(⟨exp⟩
   /ν0_geo)`), matches the task's "prefer store `Ea_rep_eV + nu0_eff`" directive
   (`nu0_eff ≡ nu0_geo`).

2. **Units — Hz vs ps⁻¹.** *Resolution:* member ν0 come from pyKMC in **Hz**
   (`event_table` `nu0`/`k_prefactor`); the on-lattice rate unit is **ps⁻¹**
   (project note `pykmc-k0-units-clock-freeze`: `[RateConstant] k0` is ps⁻¹). Output
   columns are ps⁻¹ via `÷HZ_PER_PSINV=1e12`; `Ea_rep` is unit-invariant (the 1e12
   cancels). This is called out prominently because units are a known clock-freeze trap.

3. **Do all gates apply at ingest, or a subset?** (task-flagged.) *Resolution:* **all
   seven** apply at ingest; **G2 is conditional** on a linked forward/backward pair
   (`idx_backward`/`id_saddle`), returning `NA` otherwise; G4's round-trip uses ideal-site
   re-expansion (no runtime grid needed). Cite §8.2 (gates are ingest-time admission) and
   §7.2 (G2 needs the linked pair for the independent ⟨dE_pair⟩).

4. **Is forward projection (§2) needed in Phase A given the loop driver is out of scope?**
   *Resolution:* `projection.py` is a required Phase A module (round-trip determinism
   tests, seeding, the deterministic `to_atomistic`), but it is **independent** of the
   identity pipeline — `event_projection.py` does its own local FCC fit. The **runtime
   grid SoA** and the grid-level reverse map are out of scope; only the ingest `Occupancy`
   dict and the minimal `to_atomistic` are in. Cite §2 (project), §7.3 (`R≡I` reverse
   map), and COMPARISON §4 ("no C changes").

5. **`self_reverse`/pairing extent.** *Resolution:* Phase A implements `is_self_reverse`
   (κ property, §7.2, Sym-5), the **linked-pair** path (backward_class, dE_pair, dEnergy),
   and the real G2 test. `synthesize_balanced` reverses (one-sided harvest) are
   **specified but optional** in Phase A (emit flagged-`pending` if generated, else
   `pair_status="unpaired"` + `PAIR_CLOSURE` audit) — the *runtime* consumer that would
   ratchet without them is out of scope. Cite §7.2.

6. **`move_shape`/`family_id` when the fallback regressor (§6.2) is out of scope.**
   *Resolution:* compute them (cheap, deterministic, §7.4) so the schema is stable for
   Phase B, but the regressor that consumes `family_id` is **not** built. `phi`,
   `model_version`, `fallback_stats` are left empty and omitted from the Parquet. Cite
   §1.3 (schema) and §6.2 (deferred consumer).

7. **Anchor tie-breaking without a frame-dependent `lex(offset)` (Sym-2).**
   *Resolution:* the reference semantics is **full enumeration** over all moved sites ×
   all 16 ops; the `min` over the joint integer tuple is anchor/order-independent by
   construction, so no tie-break enters `class_id`. For the stored `(a*, g*)` orientation
   (execution frame), break residual ties by `(mover_index_ascending, op_index_ascending)`
   — this affects only which equivalent orientation is recorded, never the key. The §4.2
   G-invariant pruning keys are an **optional** optimisation. Cite §4.2/§4.3.

8. **Which `event_id` role — identity or screening?** *Resolution:* `event_id` is a
   single-atom, frame-inconsistent graph certificate; used **only** as an ingest screening
   bucket (bucket by `id_saddle`), never as identity. The refines-`id_saddle`-in-rate-units
   test (§4.4/M6) guards fan-out/fold-in. `sym_matrix`/`sym_perm` realizability
   cross-check (§4.7) is **deferred** past Phase A (leave a stub hook). Cite §4.4, §4.6,
   §4.7.

---

## 13. Deviations from FINAL_DESIGN (Phase A) — summary

- **Runtime types not built.** `Grid` (SoA), `OrientedPattern`, `Instance`, and the
  runtime matching (§5) / group-BKL / incremental invalidation are **not** Phase A
  (COMPARISON §4: "pure Python, no C changes"). `EventClass` is the sole persisted object.
- **`Occupancy` is a sparse `dict[Offset, Occ]`**, not the runtime dense tiled SoA — the
  ingest side never allocates the production grid. Deviation justified: identity +
  catalogue emission need no dense grid; the SoA is Phase C.
- **`to_atomistic` is the minimal ingest reverse map** (sorted-site ideal `R≡I` emission),
  not the full flagged-priority grid reverse map of §7.3. Sufficient for the round-trip
  test; full version is Phase D.
- **`Ea_std` shrinkage estimator pinned** to `sqrt(max(sample_var, 0.02²))` for n≥3 /
  `None` for n<3 (design §6.1 says only "shrinkage with a prior floor" — a concrete floor
  is chosen and surfaced as constant `PRIOR_EA_STD_FLOOR_EV`).
- **`synthesize_balanced` reverse optional** in Phase A (see §12.5).
- **`sym_matrix`/`sym_perm` cross-check (§4.7) deferred** (stub hook only).

None of these change a `class_id`, a rate, or a gate outcome relative to the design's
intent; they bound Phase A to the ingest layer.
