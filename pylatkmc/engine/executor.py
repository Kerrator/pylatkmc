# pylatkmc/engine/executor.py
"""The BKL/n-fold-way executor: eligibility, event enumeration, and (Task 7) the
step loop. Eligibility is a pure function of lattice state, so a full rescan each
step is exact — the C decision tree is only a perf optimization."""

from __future__ import annotations

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
