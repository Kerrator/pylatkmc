# tests/unit_py/test_engine_step.py
import pathlib
import sys

from pylatkmc.engine.catalogue import compile_catalogue
from pylatkmc.engine.executor import step_once
from pylatkmc.engine.rng import make_rng
from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import SPECIES  # noqa: E402
from _engine_fixtures import mini_lattice as _mini_lattice  # noqa: E402
from _engine_fixtures import px_hop_gated as _px_hop_gated  # noqa: E402


def test_step_once_applies_hop_and_advances_time():
    lat = _mini_lattice()  # 0(vac)-1(Ni)-2(Ni)
    st = state_from_lattice(lat)
    compiled = compile_catalogue([_px_hop_gated(1)], SPECIES)
    rng = make_rng(7, 0)
    out = step_once(lat, st, compiled, rng)
    assert out is not None
    assert out.proc_id == 0 and out.site == 0
    assert out.dt > 0.0
    # vacancy moved from site 0 to site 1; species swapped.
    assert st.species[0] == 1  # Ni now at site 0
    assert st.species[1] == 0  # vacancy now at site 1
    assert st.vac_list == [1]
    assert st.time_s == out.dt
    assert st.step == 1
    assert st.mean_msd_A2() == 1.0


def test_step_once_returns_none_when_no_events():
    lat = _mini_lattice()
    st = state_from_lattice(lat)
    # empty catalogue -> no events -> step_once returns None.
    compiled = compile_catalogue([], SPECIES)
    assert step_once(lat, st, compiled, make_rng(1, 0)) is None
