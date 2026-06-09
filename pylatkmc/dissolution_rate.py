"""Erlebacher/MESOSIM electrochemical dissolution rate (shared reference).

Coordination- and potential-dependent dissolution of a surface atom:

    k = nu_E * exp( -(E_bare - phi) / (kB * T) )
    E_bare = sum_j eps(mover, neighbour_j)   over OCCUPIED nearest neighbours

``E_bare`` is the *bare* bond-breaking barrier -- the quantity baked into each
engine's rate table. ``phi`` (the overpotential term, in energy units) is
applied at RUNTIME so one compiled model runs at any applied potential. The
per-bond energies ``eps`` are anchored to DFT (Ke & Taylor 2020): a
~9-coordinated Ni terrace atom has ``E_bare ~ 1.8 eV`` => ``eps_NiNi ~ 0.2
eV/bond``. The canonical parameter table and its provenance live in
``apps/PyKMC_Analysis/Analysis/dissolution/epsilon_table.toml``.

This module is duplicated BYTE-FOR-BYTE in:
  - pylatkmc/pylatkmc/dissolution_rate.py    (used at codegen time)
  - pyKMC-develop/pykmc/dissolution_rate.py  (used at runtime)
A test in each package asserts the two copies agree on a fixed grid. It is
pure-stdlib (``math`` only at the hot path) so it imports cleanly in both
packages with no extra dependency. Do NOT add engine imports here.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib  # stdlib
else:
    import tomli as tomllib  # type: ignore[no-redef]

# Boltzmann constant in eV/K. MUST equal pylatkmc.rate_expression.KB_EV_PER_K so
# the Python-baked E_bare and the C-runtime Arrhenius cannot drift.
KB_EV_PER_K = 8.617333e-5  # eV/K


def _canon(a: str, b: str) -> tuple[str, str]:
    """Canonical unordered species-pair key (lexicographically sorted)."""
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class DissolutionParams:
    """Parameters for the Erlebacher dissolution rate law.

    Attributes
    ----------
    epsilon : dict[tuple[str, str], float]
        Per-bond energies (eV), keyed by canonical unordered species pair
        (lexicographically sorted tuple), e.g. ``("Ni", "Ni") -> 0.200``.
    nu_E_Hz : float
        Dissolution attempt frequency (Hz). ~1e4 (exchange-current derived),
        NOT the 1e13 Debye prefactor used for diffusion.
    phi_eV : float
        Default overpotential term (eV); usually overridden at runtime.
    max_coordination, min_coordination : int
        The MESOSIM gate -- only atoms with min..max occupied nearest
        neighbours dissolve.

    """

    epsilon: dict[tuple[str, str], float]
    nu_E_Hz: float = 1.0e4
    phi_eV: float = 0.0
    max_coordination: int = 9
    min_coordination: int = 3


def eps(params: DissolutionParams, a: str, b: str) -> float:
    """Per-bond energy ``eps(a, b)`` in eV (symmetric).

    Raises KeyError if the pair is absent (never silently 0).
    """
    key = _canon(a, b)
    try:
        return params.epsilon[key]
    except KeyError as exc:
        raise KeyError(
            f"no per-bond energy for pair {key}; known pairs: {sorted(params.epsilon)}"
        ) from exc


def e_bare(
    params: DissolutionParams, mover: str, neighbour_hist: dict[str, int]
) -> float:
    """Bare bond-breaking barrier over the occupied neighbour histogram.

    ``E_bare = sum_sp eps(mover, sp) * n_sp``; ``"Vacant"`` entries (and zero
    counts) contribute nothing.
    """
    total = 0.0
    for sp, n in neighbour_hist.items():
        if sp == "Vacant" or n == 0:
            continue
        total += eps(params, mover, sp) * n
    return total


def dissolution_rate(
    params: DissolutionParams,
    mover: str,
    neighbour_hist: dict[str, int],
    T_K: float,
    phi_eV: float | None = None,
) -> float:
    """Erlebacher dissolution rate ``k = nu_E * exp(-(E_bare - phi)/(kB*T))``.

    ``phi_eV`` overrides ``params.phi_eV`` when given. The effective barrier is
    clamped at 0 (barrierless dissolution at high overpotential).
    """
    if not (T_K > 0):
        raise ValueError(f"T_K must be positive; got {T_K}")
    phi = params.phi_eV if phi_eV is None else phi_eV
    barrier = e_bare(params, mover, neighbour_hist) - phi
    if barrier < 0.0:
        barrier = 0.0
    return float(params.nu_E_Hz * math.exp(-barrier / (KB_EV_PER_K * T_K)))


def load_params(path: str | Path) -> DissolutionParams:
    """Load a :class:`DissolutionParams` from an ``epsilon_table.toml`` file."""
    p = Path(path)
    with p.open("rb") as f:
        raw = tomllib.load(f)
    meta = raw.get("meta", {})
    eps_raw = raw.get("epsilon_eV_per_bond", {})
    epsilon: dict[tuple[str, str], float] = {}
    for k, v in eps_raw.items():
        parts = k.split("-")
        if len(parts) != 2:
            raise ValueError(f"malformed epsilon key {k!r}; expected 'A-B'")
        epsilon[_canon(parts[0].strip(), parts[1].strip())] = float(v)
    return DissolutionParams(
        epsilon=epsilon,
        nu_E_Hz=float(meta.get("nu_E_Hz", 1.0e4)),
        phi_eV=float(meta.get("default_phi_eV", 0.0)),
        max_coordination=int(meta.get("max_coordination", 9)),
        min_coordination=int(meta.get("min_coordination", 3)),
    )


__all__ = (
    "KB_EV_PER_K",
    "DissolutionParams",
    "eps",
    "e_bare",
    "dissolution_rate",
    "load_params",
)
