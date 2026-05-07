"""Model specification — the stable contract between the TOML spec, the
code generator, and the rate-data builder.

A ModelSpec fully determines:
  - which species exist in the rate key and in which roles (mover vs shell)
  - which neighbour shells are scanned and what they count
  - the ordered list of key axes that index the rate cube
  - the rate-data source files and the physics parameters (T, k0)

Everything the generator emits is a pure function of ModelSpec. The TOML
loader is kept in loader.py; this file only defines the data shape and
its invariants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ------------------------------------------------------------------
# Compile-time limits. Raise these deliberately; the cube size grows
# multiplicatively so a bigger limit means a bigger .kmcrt on disk.
# ------------------------------------------------------------------
MAX_COUNT_CAP = 8  # per-axis bin cap
MAX_CUBE_ENTRIES = 100_000_000  # hard stop at ~1.2 GB cube

# Fixed axes that exist in every spec. Extra axes live in ModelSpec.key.axes.
PERMANENT_AXES: tuple[str, ...] = ("site_class", "direction")


class Shell(BaseModel):
    """A neighbour shell. The generator emits one scan_shell pass per shell.

    `name` must be unique within a spec and is referenced by KeyAxis.shell.
    `cutoff_mult` is the upper bound of the shell, in units of the 1NN
    distance. For FCC: 1NN ~ 1.0, 2NN ~ sqrt(2) ~ 1.414.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    cutoff_mult: float = Field(gt=0.0, le=3.0)

    @field_validator("name")
    @classmethod
    def _name_simple(cls, v: str) -> str:
        if not v.isidentifier() or "__" in v:
            raise ValueError(f"shell name {v!r} must be a simple identifier")
        return v


class KeyAxis(BaseModel):
    """One dimension of the rate-cube key.

    Two kinds:
      kind='enum'  — values are an enum with `max` variants (e.g. site_class,
                     direction, mover_species). The generator emits an integer
                     0..max-1 per row.
      kind='count' — a species-count over one shell, bucketed 0..max-1. The
                     generator emits a scalar counter variable in scan_shell
                     that increments when species[neighbor] == match.

    The permanent axes `site_class` and `direction` are implicitly axis 0 and 1
    and do not appear in ModelSpec.key.axes; user-specified axes start at 2.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    kind: Literal["enum", "count"]
    max: int = Field(gt=0, le=MAX_COUNT_CAP)

    # Only for kind='count'
    shell: str | None = None
    match: str | None = None  # species name, or literal "vac"

    # Only for kind='enum' with a species role
    skip_vacant: bool = False  # True => mover_species only enumerates non-vacant

    @field_validator("name")
    @classmethod
    def _name_simple(cls, v: str) -> str:
        if not v.isidentifier() or "__" in v:
            raise ValueError(f"axis name {v!r} must be a simple identifier")
        return v

    @model_validator(mode="after")
    def _shape_consistent(self) -> KeyAxis:
        if self.kind == "count":
            if self.shell is None or self.match is None:
                raise ValueError(f"count axis {self.name!r} requires shell and match")
        else:  # enum
            if self.shell is not None or self.match is not None:
                raise ValueError(f"enum axis {self.name!r} cannot specify shell/match")
        return self


class Key(BaseModel):
    """Ordered list of user-specified key axes. The permanent axes site_class
    (3 values) and direction (5 values) are prepended implicitly at codegen."""

    model_config = ConfigDict(frozen=True)

    axes: list[KeyAxis]

    @field_validator("axes")
    @classmethod
    def _unique_names(cls, v: list[KeyAxis]) -> list[KeyAxis]:
        names = [a.name for a in v]
        for permanent in PERMANENT_AXES:
            if permanent in names:
                raise ValueError(f"axis name {permanent!r} is reserved (implicit permanent axis)")
        if len(set(names)) != len(names):
            dups = {n for n in names if names.count(n) > 1}
            raise ValueError(f"duplicate axis names: {sorted(dups)}")
        return v


class RateData(BaseModel):
    """Paths to the training data and the physics parameters."""

    model_config = ConfigDict(frozen=True)

    primary: Path  # classified_events_with_families.csv
    family_table: Path | None = None  # rate_lookup_table_family.csv (tier-6 fallback)
    fallback_scalar: Path | None = None  # rate_lookup_table.csv (tier-7 fallback, <110> only)
    temperature_K: float = Field(gt=0.0)
    k0_Hz: float = Field(gt=0.0)

    @field_validator("primary", "family_table", "fallback_scalar")
    @classmethod
    def _absolute_or_relative(cls, v: Path | None) -> Path | None:
        # Paths are left unresolved here; the loader is responsible for rooting
        # them relative to the spec file's directory if relative.
        return v


class ModelSpec(BaseModel):
    """Top-level specification for a compiled pylatkmc model.

    A single .kmcspec.toml deserialises into one ModelSpec. Everything the
    codegen and rate builder do is a pure function of this struct.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    lattice: Literal["fcc"] = "fcc"  # scope-locked to FCC in this iteration
    species: list[str]  # first element must be "Vacant"
    shells: list[Shell]
    key: Key
    rate_data: RateData

    # --------------------------------------------------------------
    # Invariants beyond what pydantic field validators can express.
    # --------------------------------------------------------------
    @field_validator("name")
    @classmethod
    def _name_simple(cls, v: str) -> str:
        if not v.isidentifier() or "__" in v:
            raise ValueError(f"model name {v!r} must be a simple identifier")
        return v

    @field_validator("species")
    @classmethod
    def _species_starts_with_vacant(cls, v: list[str]) -> list[str]:
        if not v or v[0] != "Vacant":
            raise ValueError(
                f"species list must start with 'Vacant'; got {v[0] if v else '<empty>'!r}"
            )
        if len(set(v)) != len(v):
            raise ValueError(f"duplicate species in list: {v}")
        return v

    @model_validator(mode="after")
    def _shells_and_axes_cross_check(self) -> ModelSpec:
        shell_names = {s.name for s in self.shells}
        species_set = set(self.species) | {"vac"}  # 'vac' is alias for Vacant
        for axis in self.key.axes:
            if axis.kind == "count":
                if axis.shell not in shell_names:
                    raise ValueError(
                        f"axis {axis.name!r} references unknown shell "
                        f"{axis.shell!r}; known: {sorted(shell_names)}"
                    )
                if axis.match not in species_set:
                    raise ValueError(
                        f"axis {axis.name!r} matches unknown species "
                        f"{axis.match!r}; known: {sorted(species_set)}"
                    )
        return self

    @model_validator(mode="after")
    def _cube_size_within_cap(self) -> ModelSpec:
        n = self.n_cube_entries()
        if n > MAX_CUBE_ENTRIES:
            raise ValueError(
                f"model cube has {n:,} entries which exceeds "
                f"MAX_CUBE_ENTRIES={MAX_CUBE_ENTRIES:,}. Reduce max on some "
                f"count axes or remove axes."
            )
        return self

    # --------------------------------------------------------------
    # Derived quantities used by the generator and rate builder.
    # --------------------------------------------------------------
    def all_axes(self) -> list[tuple[str, int]]:
        """Full axis list (permanent + user-specified) as (name, max_bin) tuples.
        The generator iterates this to emit the flat-key expression."""
        permanent = [("site_class", 3), ("direction", 5)]
        user = [(a.name, a.max) for a in self.key.axes]
        return permanent + user

    def n_cube_entries(self) -> int:
        n = 1
        for _, m in self.all_axes():
            n *= m
        return n

    def strides(self) -> list[int]:
        """Row-major strides for a flat key index (last axis is stride 1)."""
        axes = self.all_axes()
        strides = [1] * len(axes)
        for i in range(len(axes) - 2, -1, -1):
            strides[i] = strides[i + 1] * axes[i + 1][1]
        return strides

    def counted_species_in_shell(self, shell_name: str) -> list[str]:
        """Return the list of species (except 'vac') counted in `shell_name`.
        The generator uses this to emit the else-if cascade in scan_shell."""
        out: list[str] = []
        for axis in self.key.axes:
            if axis.kind == "count" and axis.shell == shell_name and axis.match != "vac":
                out.append(axis.match)  # type: ignore[arg-type]  # mypy: covered by validator
        return out

    def has_mover_species_axis(self) -> bool:
        return any(a.name == "mover_species" for a in self.key.axes)

    def axis_index(self, name: str) -> int:
        """Return the 0-based position of `name` in all_axes(). KeyError if unknown."""
        for i, (n, _) in enumerate(self.all_axes()):
            if n == name:
                return i
        raise KeyError(f"unknown axis: {name!r}")

    def linear_index(self, key_values: tuple[int, ...]) -> int:
        """Flatten an N-tuple key (in all_axes() order) to a cube index.

        Raises ValueError if any value is out of range for its axis.
        """
        axes = self.all_axes()
        if len(key_values) != len(axes):
            raise ValueError(f"expected {len(axes)} key values, got {len(key_values)}")
        strides = self.strides()
        out = 0
        for v, (name, max_bin), s in zip(key_values, axes, strides, strict=True):
            if v < 0 or v >= max_bin:
                raise ValueError(f"axis {name!r} value {v} out of range [0, {max_bin})")
            out += v * s
        return out
