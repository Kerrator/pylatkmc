# pylatkmc/engine/state.py
"""Mutable per-replica simulation state: species array, vacancy bookkeeping, and
per-vacancy unwrapped displacement for MSD."""

from __future__ import annotations

import numpy as np

from pylatkmc.engine.catalogue import SPECIES_STUB
from pylatkmc.engine.lattice import Lattice


def _min_image(d: np.ndarray, cell: tuple[float, float, float]) -> np.ndarray:
    out: np.ndarray = d.astype(np.float64).copy()
    for k in range(3):
        L = cell[k]
        if out[k] > 0.5 * L:
            out[k] -= L
        elif out[k] < -0.5 * L:
            out[k] += L
    return out


class State:
    def __init__(self, lat: Lattice) -> None:
        n = lat.n_sites
        self.n_sites = n
        # species padded with one stub slot at index n.
        self.species = np.empty(n + 1, dtype=np.uint8)
        self.species[:n] = lat.initial_species
        self.species[n] = SPECIES_STUB
        self.vac_list: list[int] = [int(s) for s in np.flatnonzero(lat.initial_species == 0)]
        self.vac_idx_of: dict[int, int] = {s: i for i, s in enumerate(self.vac_list)}
        self.n_vac = len(self.vac_list)
        self.time_s = 0.0
        self.step = 0
        # per-initial-vacancy unwrapped displacement; slot = initial vacancy order.
        self.disp = np.zeros((max(self.n_vac, 1), 3), dtype=np.float64)
        # current vacancy site -> displacement slot.
        self.vac_slot: dict[int, int] = {s: i for i, s in enumerate(self.vac_list)}

    def mean_msd_A2(self) -> float:
        if self.n_vac == 0:
            return 0.0
        sq = (self.disp[: self.n_vac] ** 2).sum(axis=1)
        return float(sq.mean())

    def move_vacancy(self, lat: Lattice, src: int, dst: int) -> None:
        """Move a vacancy from site ``src`` to site ``dst`` and accumulate its
        unwrapped displacement. Caller has already updated ``self.species``."""
        slot = self.vac_slot.pop(src)
        self.vac_slot[dst] = slot
        d = lat.positions[dst].astype(np.float64) - lat.positions[src].astype(np.float64)
        self.disp[slot] += _min_image(d, lat.cell)
        # keep vac_list / vac_idx_of consistent
        i = self.vac_idx_of.pop(src)
        self.vac_list[i] = dst
        self.vac_idx_of[dst] = i


def state_from_lattice(lat: Lattice) -> State:
    return State(lat)
