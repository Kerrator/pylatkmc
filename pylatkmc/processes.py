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

- `CoordOffset` uses `(di, dj, dk, sublattice)` integer offsets in the
  lattice's primitive basis. For FCC two-basis (sublattice in {"a", "b"})
  this expresses an arbitrary lattice neighbour without baking in the
  Cartesian geometry. The runtime resolves coords against its CSR
  neighbour list.
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
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_FROZEN = ConfigDict(frozen=True, str_strip_whitespace=True)


class CoordOffset(BaseModel):
    """A site offset relative to a process's anchor site.

    `(di, dj, dk)` are integer steps in the lattice's primitive basis.
    `sublattice` selects which basis atom of a multi-basis lattice (FCC
    has two basis atoms per primitive cell — "a" and "b"; BCC has one;
    HCP has two; etc.).

    The anchor is the origin (0, 0, 0, "a") by convention. Conditions /
    Actions / Bystanders all use offsets relative to that anchor.
    """

    model_config = _FROZEN

    di: int
    dj: int
    dk: int
    sublattice: Literal["a", "b"]

    def __str__(self) -> str:
        return f"({self.di},{self.dj},{self.dk},{self.sublattice})"


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


__all__ = (
    "CoordOffset",
    "Condition",
    "Action",
    "Bystander",
    "Process",
)
