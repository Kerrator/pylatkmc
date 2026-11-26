# tests/unit_py/test_engine_eligibility.py
import pathlib
import sys

import numpy as np

from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.engine.executor import enumerate_events, is_eligible
from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import SPECIES  # noqa: E402
from _engine_fixtures import mini_lattice as _mini_lattice  # noqa: E402
from _engine_fixtures import px_hop_gated as _px_hop_gated  # noqa: E402


def test_eligibility_respects_conditions_and_exact_shell_count():
    lat = _mini_lattice()  # sites 0(vac)-1(Ni)-2(Ni); site0 only has +x neighbour
    st = state_from_lattice(lat)
    # mover = site1 (NC_NN1_PX of anchor 0). Its 1NN shell = {0, 2}; vacant count = 1 (site0).
    compiled_ok = compile_catalogue([_px_hop_gated(1)], SPECIES)
    assert is_eligible(lat, st, compiled_ok[0], anchor=0) is True
    # exact-count gate: count=0 must NOT fire (there IS 1 vacant 1NN).
    compiled_no = compile_catalogue([_px_hop_gated(0)], SPECIES)
    assert is_eligible(lat, st, compiled_no[0], anchor=0) is False


def test_enumerate_events_only_at_vacancy_anchors():
    lat = _mini_lattice()
    st = state_from_lattice(lat)
    compiled = compile_catalogue([_px_hop_gated(1)], SPECIES)
    pairs, rates, r_tot = enumerate_events(lat, st, compiled)
    assert pairs == [(0, 0)]  # proc 0 at anchor site 0 only
    assert r_tot == 2.0
    assert np.allclose(rates, [2.0])
