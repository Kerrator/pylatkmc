# pylatkmc/engine/executor.py
"""The BKL/n-fold-way executor: eligibility, event enumeration, and (Task 7) the
step loop. Eligibility is a pure function of lattice state, so a full rescan each
step is exact — the C decision tree is only a perf optimization."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from pylatkmc.engine.catalogue import CompiledProcess
from pylatkmc.engine.lattice import Lattice
from pylatkmc.engine.state import State


def count_in_shell(
    lat: Lattice, st: State, site: int, shell_kind: int, species_idx: int
) -> int:
    if site >= lat.n_sites:  # stub site has no shell
        return 0
    if shell_kind == 0:
        b, e = int(lat.nn1_offsets[site]), int(lat.nn1_offsets[site + 1])
        nbrs = lat.nn1_indices[b:e]
    else:
        b, e = int(lat.nn2_offsets[site]), int(lat.nn2_offsets[site + 1])
        nbrs = lat.nn2_indices[b:e]
    return int(np.count_nonzero(st.species[nbrs] == species_idx))


def is_eligible(lat: Lattice, st: State, cp: CompiledProcess, anchor: int) -> bool:
    ct = lat.coord_table[anchor]
    for code_idx, sp in cp.conds:
        if st.species[ct[code_idx]] != sp:
            return False
    for code_idx, kind, sp, count in cp.shells:
        site = int(ct[code_idx])
        if count_in_shell(lat, st, site, kind, sp) != count:
            return False
    return True


def enumerate_events(
    lat: Lattice, st: State, compiled: list[CompiledProcess]
) -> tuple[list[tuple[int, int]], np.ndarray, float]:
    """Return (pairs, rates, r_tot). Anchors are scanned by each process's
    anchor_species; in v2 every process anchors on Vacant, so the scan set is the
    vacancy list."""
    # Group anchor candidates by species value present in the state.
    pairs: list[tuple[int, int]] = []
    rate_list: list[float] = []
    # vacancy sites are the only anchor candidates for Vacant-anchored processes.
    vac_sites = st.vac_list
    for proc_id, cp in enumerate(compiled):
        if cp.anchor_species == 0:  # Vacant
            candidates = vac_sites
        else:
            candidates = [
                s for s in range(lat.n_sites) if st.species[s] == cp.anchor_species
            ]
        for s in candidates:
            if is_eligible(lat, st, cp, s):
                pairs.append((proc_id, s))
                rate_list.append(cp.rate)
    rates = np.asarray(rate_list, dtype=np.float64)
    return pairs, rates, float(rates.sum())


@dataclass
class EventOutcome:
    proc_id: int
    site: int
    dt: float
    r_tot: float
    k_event: float
    Ea_eV: float


def step_once(
    lat: Lattice,
    st: State,
    compiled: list[CompiledProcess],
    rng: np.random.Generator,
) -> EventOutcome | None:
    pairs, rates, r_tot = enumerate_events(lat, st, compiled)
    if not pairs or r_tot <= 0.0:
        return None
    u1, u2 = rng.random(), rng.random()
    target = u1 * r_tot
    cum = np.cumsum(rates)
    idx = int(np.searchsorted(cum, target, side="right"))
    if idx >= len(pairs):
        idx = len(pairs) - 1
    proc_id, site = pairs[idx]
    cp = compiled[proc_id]
    dt = -math.log(u2) / r_tot if u2 > 0.0 else 0.0

    ct = lat.coord_table[site]
    # verify + apply atomically
    targets = [(int(ct[code]), before, after) for code, before, after in cp.actions]
    for resolved, before, _after in targets:
        if int(st.species[resolved]) != before:
            raise RuntimeError(
                f"apply precondition failed for {cp.name!r} at site {site}: "
                f"site {resolved} is {int(st.species[resolved])}, expected {before}"
            )
    for resolved, _before, after in targets:
        st.species[resolved] = after

    src = int(ct[cp.v_from_code])
    dst = int(ct[cp.v_to_code])
    if src != dst:
        st.move_vacancy(lat, src=src, dst=dst)

    st.time_s += dt
    st.step += 1
    return EventOutcome(
        proc_id=proc_id, site=site, dt=dt, r_tot=r_tot, k_event=cp.rate, Ea_eV=cp.Ea_eV
    )
