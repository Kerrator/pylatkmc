"""Pattern-DB IR for pylatkmc v2.

A `Process` describes a single kinetic mechanism on the lattice. Each
process has:

- A list of **Conditions** that must all be true at specific
  lattice-relative offsets for the process to be eligible to fire.
- A list of **Actions** that are applied atomically when the process
  fires, changing species at one or more sites.
- An optional list of **Bystanders** — sites whose species don't gate
  the process but whose count modulates the rate (kmos OTF semantics).
- A rate expression that may be a scalar (`k0 * exp(-Ea/kT)` baked at
  codegen time) or count-dependent if Bystanders are present.

Multi-site processes (cooperative 1NN hops, triple hops, exchanges) are
represented by `len(actions) >= 2`. The runtime applies all actions in
one transactional update.

This IR is consumed by:
- `pylatkmc.translator` — produces a list[Process] from a curated catalogue
- `pylatkmc.decision_tree` — compiles a list[Process] into nested-switch C
- `pylatkmc.codegen` — emits the runtime's `proclist.c`

The IR is **frozen and hashable** so that golden-file tests can compare
emitted C against an expected list[Process] deterministically.

Conventions:

- `CoordOffset` carries a single **`NeighbourCode`** string naming a
  specific neighbour direction relative to the anchor (e.g. `"NC_NN1_PX"`,
  `"NC_NN1_UP_PP"`). The runtime resolves these via a per-site lookup
  table (see `runtime/src/core/coord_codes.h` for the canonical
  Cartesian deltas, and `lattice_build_coord_table` for the resolver).
  This replaces the older `(di, dj, dk, sublattice)` IR which couldn't
  cleanly express FCC cross-layer 1NN — see § "The coord-resolution gap"
  in `~/.claude/plans/eager-sauteeing-dragon.md`.
- `Condition.species` and `Action.before`/`after` use the species names
  declared in the model spec (e.g. "Vacant", "Ni", "Fe", "Cr").
- `Bystander.allowed_species` is a whitelist; sites whose species is
  outside the whitelist contribute zero to the count.
- `Bystander.flag` groups bystanders into named shells (e.g. "1nn",
  "2nn"); the runtime exposes a counter per (species, flag) pair.

References:
- kmos's `Process` / `ConditionAction` / `Bystander` schema:
  `_archive/kmos-main/kmos/types.py:2024–2255`
- kmos's decision-tree compilation:
  `_archive/kmos-main/kmos/io/__init__.py:2568–2655`
- kmos's `Coord(name, offset, layer)` direction-resolution scheme that
  inspired the NeighbourCode design:
  `_archive/kmos-main/kmos/types.py:1778`
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_FROZEN = ConfigDict(frozen=True, str_strip_whitespace=True)


# Valid NeighbourCode names. MUST stay in sync with the C enum in
# `runtime/src/core/coord_codes.h`. The order here is informational only;
# only set membership matters for validation.
NEIGHBOUR_CODES: tuple[str, ...] = (
    "NC_ANCHOR",
    # In-plane axial 1NN
    "NC_NN1_PX", "NC_NN1_MX", "NC_NN1_PY", "NC_NN1_MY",
    # Cross-layer 1NN going DOWN
    "NC_NN1_DOWN_PP", "NC_NN1_DOWN_PM", "NC_NN1_DOWN_MP", "NC_NN1_DOWN_MM",
    # Cross-layer 1NN going UP
    "NC_NN1_UP_PP",   "NC_NN1_UP_PM",   "NC_NN1_UP_MP",   "NC_NN1_UP_MM",
    # In-plane diagonal 2NN
    "NC_NN2_DIAG_PP", "NC_NN2_DIAG_PM", "NC_NN2_DIAG_MP", "NC_NN2_DIAG_MM",
    # Axial 2NN
    "NC_NN2_PX", "NC_NN2_MX", "NC_NN2_PY", "NC_NN2_MY", "NC_NN2_PZ", "NC_NN2_MZ",
)
_NEIGHBOUR_CODE_SET = frozenset(NEIGHBOUR_CODES)

# Type alias used by Condition/Action/Bystander field annotations. We use a
# plain `str` + a field_validator (rather than a Literal[...]) so the IR can
# evolve without forcing every Pydantic version to re-process a 23-element
# Literal.
NeighbourCodeStr = str


class CoordOffset(BaseModel):
    """A site offset relative to a process's anchor site.

    A CoordOffset is named by a single **NeighbourCode** string (e.g.
    `"NC_ANCHOR"` for the anchor itself, `"NC_NN1_PX"` for the +x in-plane
    1NN, `"NC_NN1_UP_PP"` for the cross-layer-up 1NN with positive x and
    positive y in-plane components). The complete set of valid codes is
    in `NEIGHBOUR_CODES`; the canonical Cartesian delta of each code is
    in `runtime/src/core/coord_codes.{h,c}`.

    For an anchor site `s`, the runtime resolves a CoordOffset via
    `lat->coord_table[s * N_NEIGHBOUR_CODES + code_idx]`, which returns
    the absolute site index of the named neighbour (or -1 if `s` doesn't
    have that neighbour, e.g. a surface site has no `NC_NN1_UP_*`).
    """

    model_config = _FROZEN

    code: NeighbourCodeStr = Field(
        ...,
        description="NeighbourCode name; must appear in NEIGHBOUR_CODES.",
    )

    @field_validator("code")
    @classmethod
    def _check_known(cls, v: str) -> str:
        if v not in _NEIGHBOUR_CODE_SET:
            raise ValueError(
                f"unknown NeighbourCode {v!r}; valid codes are: "
                f"{sorted(NEIGHBOUR_CODES)}"
            )
        return v

    def __str__(self) -> str:
        return self.code


class Condition(BaseModel):
    """A site that must hold a specific species for the process to fire.

    All Conditions of a process are ANDed; if any fails, the process is
    not eligible at that anchor site.
    """

    model_config = _FROZEN

    coord: CoordOffset
    species: str = Field(..., min_length=1)


class Action(BaseModel):
    """A site whose species changes when the process fires.

    `before` is the required pre-state (must equal the matching
    Condition's species at the same coord, when one exists; redundant
    but explicit for catching codegen bugs).

    `after` is the post-state set when the process fires.

    Multi-Action processes apply all actions in one atomic update. If
    any `before` doesn't match the live state, the runtime rolls back
    and signals a codegen bug (this should be unreachable if the
    decision tree is correct).
    """

    model_config = _FROZEN

    coord: CoordOffset
    before: str = Field(..., min_length=1)
    after: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_state_change(self) -> "Action":
        if self.before == self.after:
            raise ValueError(
                f"Action at {self.coord} has before == after == "
                f"{self.before!r}; an Action must change state. Use a "
                f"Bystander or simply omit if no change."
            )
        return self


class Bystander(BaseModel):
    """A site whose species count modulates the rate but doesn't gate
    eligibility.

    `allowed_species` is a whitelist of species that contribute to the
    `nr_<species>_<flag>` counter at runtime. A Bystander whose live
    species is outside the whitelist contributes 0 (and doesn't block
    the process from firing — that's what distinguishes it from a
    Condition).

    `flag` groups Bystanders into shells (e.g. "1nn" for first-neighbour,
    "2nn" for second-neighbour). The codegen emits one counter per
    (species, flag) pair.
    """

    model_config = _FROZEN

    coord: CoordOffset
    allowed_species: tuple[str, ...] = Field(..., min_length=1)
    flag: str = Field(..., min_length=1)

    @field_validator("allowed_species")
    @classmethod
    def _check_unique(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(v)) != len(v):
            raise ValueError(f"allowed_species must be unique; got {v!r}")
        return v


class Process(BaseModel):
    """A single kinetic mechanism on the lattice.

    A Process is **eligible** at lattice anchor site `s` iff every
    Condition's species matches `state.species[resolve(s, coord)]`.
    When fired:
      1. Every Action is applied atomically.
      2. The rate (used by BKL selection) was computed at codegen time
         (or, with Bystanders, modulated at touchup time) from
         `rate_constant_eV` and the Bystander counts.

    The runtime maintains a per-Process `avail_sites[]` index (the set
    of currently-eligible anchor sites for this Process) and a
    cumulative-rate sum for BKL.

    Attributes
    ----------
    name : str
        Stable identifier. Convention: `<family_id>__<bucket_id>__<arrangement>`.
        Used as the C function name for `apply_actions_<name>`, so it
        must be a valid C identifier (no dots, dashes, etc.).
    family_id : str
        Back-link to the upstream curated family (e.g. "surface_1NN_inplane").
        Provenance for the `pylatkmc-gen processes` report.
    Ea_eV : float
        Activation energy. Logged by the runtime per fired event for
        comparison with pyKMC reference data.
    rate_constant : str | float
        Either a scalar prefactor (k0 in s^-1, baked into the rate at
        codegen time as `k0 * exp(-Ea_eV / kT)`), or an expression
        string referencing `nr_<species>_<flag>` Bystander counters.
    conditions : tuple[Condition, ...]
        ANDed boolean predicates. Empty = process always eligible at
        every anchor site (rare; usually has at least the anchor's own
        species condition).
    actions : tuple[Action, ...]
        Multi-site state changes applied atomically when fired.
    bystanders : tuple[Bystander, ...]
        Optional rate-modulating soft counts. Empty = scalar rate.
    """

    model_config = _FROZEN

    name: str = Field(..., min_length=1, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    family_id: str = Field(..., min_length=1)
    Ea_eV: float
    rate_constant: str | float
    conditions: tuple[Condition, ...]
    actions: tuple[Action, ...] = Field(..., min_length=1)
    bystanders: tuple[Bystander, ...] = ()

    @model_validator(mode="after")
    def _validate_action_before_matches_conditions(self) -> "Process":
        """Each Action's `before` should match a Condition's species at
        the same coord, OR the Action's coord must NOT have a matching
        Condition (in which case `before` is the implicit
        precondition the runtime will check at apply time)."""
        cond_by_coord: dict[CoordOffset, str] = {
            c.coord: c.species for c in self.conditions
        }
        for a in self.actions:
            if a.coord in cond_by_coord:
                expected = cond_by_coord[a.coord]
                if a.before != expected:
                    raise ValueError(
                        f"Process {self.name!r}: Action at {a.coord} "
                        f"has before={a.before!r}, but a Condition at "
                        f"the same coord requires species={expected!r}. "
                        f"They must match."
                    )
        return self

    @model_validator(mode="after")
    def _validate_bystander_no_overlap_with_conditions(self) -> "Process":
        """A coord cannot be both a Condition and a Bystander."""
        cond_coords = {c.coord for c in self.conditions}
        for b in self.bystanders:
            if b.coord in cond_coords:
                raise ValueError(
                    f"Process {self.name!r}: coord {b.coord} appears in "
                    f"both Conditions and Bystanders. Pick one."
                )
        return self

    @model_validator(mode="after")
    def _validate_Ea_finite(self) -> "Process":
        if not (self.Ea_eV >= 0):
            raise ValueError(
                f"Process {self.name!r}: Ea_eV must be non-negative; got {self.Ea_eV}"
            )
        return self


# Convenience: an "anchor" CoordOffset that IS the anchor site itself.
# Used widely by the translator.
ANCHOR_COORD = CoordOffset(code="NC_ANCHOR")


__all__ = (
    "CoordOffset",
    "Condition",
    "Action",
    "Bystander",
    "Process",
    "NEIGHBOUR_CODES",
    "ANCHOR_COORD",
)
