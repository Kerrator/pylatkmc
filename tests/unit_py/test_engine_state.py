# tests/unit_py/test_engine_state.py
import pathlib
import sys

from pylatkmc.engine.state import state_from_lattice

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _engine_fixtures import mini_lattice as _mini_lattice  # noqa: E402


def test_state_init_and_msd_tracking():
    st = state_from_lattice(_mini_lattice())
    assert st.n_vac == 1
    assert st.vac_list == [0]
    # stub sentinel present
    assert st.species[3] == 255
    assert st.mean_msd_A2() == 0.0
    # move the vacancy from site 0 to site 1: record displacement (1,0,0)
    st.move_vacancy(_mini_lattice(), src=0, dst=1)
    assert st.mean_msd_A2() == 1.0
