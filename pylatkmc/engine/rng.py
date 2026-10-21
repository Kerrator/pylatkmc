# pylatkmc/engine/rng.py
"""Reproducible per-replica RNG. Statistical parity only — this does NOT reproduce
the C runtime's xoshiro256++ stream (see the design spec, determinism section)."""

from __future__ import annotations

import numpy as np


def make_rng(base_seed: int, rank: int) -> np.random.Generator:
    """Independent, reproducible stream per (base_seed, rank)."""
    seq = np.random.SeedSequence(entropy=base_seed, spawn_key=(rank,))
    return np.random.default_rng(seq)
