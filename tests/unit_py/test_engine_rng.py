# tests/unit_py/test_engine_rng.py
from pylatkmc.engine.rng import make_rng


def test_rng_reproducible_and_rank_independent():
    a1 = make_rng(42, 0).random(5).tolist()
    a2 = make_rng(42, 0).random(5).tolist()
    b = make_rng(42, 1).random(5).tolist()
    assert a1 == a2          # same (seed, rank) -> identical stream
    assert a1 != b           # different rank -> different stream
