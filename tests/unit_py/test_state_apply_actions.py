"""Ctypes-driven tests for `state_apply_actions` (M-C.5).

The C source under test is `runtime/src/core/state_actions.c`. It applies
a list of multi-site `Action` records atomically — validate-all-then-
apply-all, with rollback on any validation failure.

Coverage:
* Single-site write: vacant→atom and atom→vacant
* Two-site hop (1NN): vacancy moves, vac_list updated
* Three-site triple hop: cascading mutations conserve vacancy count
* Validation failure: wrong `before` rejects with -EINVAL and no mutation
* Validation failure: duplicate site rejects
* Validation failure: post-apply n_vac > n_vac_max rejects
* Net-zero hop (gain + loss in same call) keeps n_vac stable
* `vac_idx_of[]` consistency after every successful apply
"""

from __future__ import annotations

import ctypes
import errno
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
RUNTIME_CORE = REPO_ROOT / "runtime" / "src" / "core"
STATE_ACTIONS_SRC = RUNTIME_CORE / "state_actions.c"
HELPERS_SRC = Path(__file__).parent / "_runtime_test_helpers.c"

EINVAL = -errno.EINVAL

# Mock species byte values — we don't depend on a generated events.h here;
# we just pick distinct uint8_t values and pass `SP_VACANT` as the
# vacant-species parameter.
SP_VACANT = 0
SP_NI = 1
SP_FE = 2
SP_CR = 3


def _have_cc() -> bool:
    return shutil.which("cc") is not None


@pytest.fixture(scope="module")
def libstate(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if not _have_cc():
        pytest.skip("cc not on PATH")
    if not STATE_ACTIONS_SRC.is_file():
        pytest.fail(f"missing source: {STATE_ACTIONS_SRC}")
    if not HELPERS_SRC.is_file():
        pytest.fail(f"missing helpers: {HELPERS_SRC}")

    builddir = tmp_path_factory.mktemp("state_actions_lib")
    libname = "libstate_actions.dylib" if os.uname().sysname == "Darwin" else "libstate_actions.so"
    libpath = builddir / libname

    cmd = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-DNDEBUG",
        "-fPIC",
        "-shared",
        "-I",
        str(RUNTIME_CORE),
        str(STATE_ACTIONS_SRC),
        str(HELPERS_SRC),
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"state_actions + helpers failed to compile:\n  stderr:\n{res.stderr}")

    lib = ctypes.CDLL(str(libpath))

    # state_apply_actions API. We pass the action array as a flat byte buffer
    # (StateAction is { int32_t site; uint8_t before; uint8_t after; padding }).
    # Use ctypes Structure to match the C layout exactly.
    class StateAction(ctypes.Structure):
        _fields_ = [
            ("site", ctypes.c_int32),
            ("before", ctypes.c_uint8),
            ("after", ctypes.c_uint8),
        ]

    lib.state_apply_actions.restype = ctypes.c_int
    lib.state_apply_actions.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(StateAction),
        ctypes.c_int32,
        ctypes.c_uint8,
    ]
    lib.StateAction = StateAction  # stash for tests to use

    # Test helpers (same shim as test_active_filter)
    lib.pylatkmc_test_make_state.restype = ctypes.c_void_p
    lib.pylatkmc_test_make_state.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
        ctypes.POINTER(ctypes.c_uint8),
    ]
    lib.pylatkmc_test_free_state.restype = None
    lib.pylatkmc_test_free_state.argtypes = [ctypes.c_void_p]
    lib.pylatkmc_test_state_n_vac.restype = ctypes.c_int32
    lib.pylatkmc_test_state_n_vac.argtypes = [ctypes.c_void_p]

    return lib


# ---------------------------------------------------------------------------
# Helper: read State fields from the C struct via ctypes
# ---------------------------------------------------------------------------


class _State:
    """RAII State wrapper that mirrors the C `State` struct's `species`,
    `vac_list`, `vac_idx_of`, and `n_vac` fields back to Python so tests
    can introspect."""

    def __init__(
        self,
        lib: ctypes.CDLL,
        n_sites: int,
        n_vac_max: int,
        species: list[int],
        vac_list: list[int],
    ) -> None:
        self.lib = lib
        self.n_sites = n_sites
        self.n_vac_max = n_vac_max

        sp_arr = (ctypes.c_uint8 * n_sites)(*species)
        vac_arr = (
            (ctypes.c_int32 * len(vac_list))(*vac_list) if vac_list else (ctypes.c_int32 * 1)(0)
        )
        h = lib.pylatkmc_test_make_state(n_sites, n_vac_max, len(vac_list), vac_arr, sp_arr)
        if not h:
            raise RuntimeError("make_state returned NULL")
        self.h = h

    def __enter__(self) -> _State:
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        if self.h is not None:
            self.lib.pylatkmc_test_free_state(self.h)
            self.h = None

    @property
    def ptr(self) -> int:
        return self.h

    # Read State fields by interpreting the struct via ctypes. The struct
    # layout (from runtime/src/core/state.h):
    #   uint8_t  *species;
    #   int32_t  *vac_list;
    #   int32_t  *vac_idx_of;
    #   int32_t   n_vac;
    #   int32_t   n_vac_max;
    #   double    time_s;
    #   uint64_t  step;
    #   double   *unwrapped_xyz;
    #   uint64_t  motif_counts[8];
    #   uint64_t  direction_counts[5];
    #
    # We use a Structure to mirror this. uintptr_t for pointer fields keeps
    # the layout valid on both 32- and 64-bit ABIs (we run 64-bit, so void*).

    @staticmethod
    def _struct_class():
        class _CState(ctypes.Structure):
            _fields_ = [
                ("species", ctypes.c_void_p),
                ("vac_list", ctypes.c_void_p),
                ("vac_idx_of", ctypes.c_void_p),
                ("n_vac", ctypes.c_int32),
                ("n_vac_max", ctypes.c_int32),
                ("time_s", ctypes.c_double),
                ("step", ctypes.c_uint64),
                ("unwrapped_xyz", ctypes.c_void_p),
                ("motif_counts", ctypes.c_uint64 * 8),
                ("direction_counts", ctypes.c_uint64 * 5),
            ]

        return _CState

    def _view(self):
        return self._struct_class().from_address(self.h)

    @property
    def n_vac(self) -> int:
        return int(self._view().n_vac)

    def species_array(self) -> list[int]:
        v = self._view()
        ptr = ctypes.cast(v.species, ctypes.POINTER(ctypes.c_uint8))
        return [int(ptr[s]) for s in range(self.n_sites)]

    def vac_list_array(self) -> list[int]:
        v = self._view()
        ptr = ctypes.cast(v.vac_list, ctypes.POINTER(ctypes.c_int32))
        return [int(ptr[i]) for i in range(self.n_vac)]

    def vac_idx_of_array(self) -> list[int]:
        v = self._view()
        ptr = ctypes.cast(v.vac_idx_of, ctypes.POINTER(ctypes.c_int32))
        return [int(ptr[s]) for s in range(self.n_sites)]


def _check_invariants(st: _State) -> None:
    """vac_list and vac_idx_of must be perfectly inverse, and species must
    agree with vac_idx_of (vacant iff vac_idx_of >= 0)."""
    species = st.species_array()
    vac_list = st.vac_list_array()
    vac_idx = st.vac_idx_of_array()
    n_vac = st.n_vac

    # Length consistency.
    assert n_vac == len(vac_list), f"n_vac {n_vac} vs vac_list len {len(vac_list)}"

    # Forward map: vac_list[k] -> site, vac_idx_of[site] should be k.
    for k, site in enumerate(vac_list):
        assert vac_idx[site] == k, (
            f"forward inverse broken: vac_list[{k}]={site}, vac_idx_of[{site}]={vac_idx[site]}"
        )

    # Reverse map: every (vac_idx_of[s] >= 0) site is vacant.
    for s in range(st.n_sites):
        idx = vac_idx[s]
        if idx >= 0:
            assert species[s] == SP_VACANT, f"site {s} has vac_idx={idx} but species={species[s]}"
            assert idx < n_vac and vac_list[idx] == s
        else:
            assert species[s] != SP_VACANT, f"site {s} has vac_idx=-1 but species==SP_VACANT"


def _apply(lib: ctypes.CDLL, st: _State, actions: list[tuple[int, int, int]]) -> int:
    """Helper: apply a list of (site, before, after) tuples."""
    SA = lib.StateAction
    n = len(actions)
    arr = (SA * n)(*[SA(site, before, after) for (site, before, after) in actions])
    return int(lib.state_apply_actions(st.ptr, arr, n, SP_VACANT))


# ---------------------------------------------------------------------------
# Empty / no-op
# ---------------------------------------------------------------------------


def test_empty_action_list_succeeds_no_change(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 8
    species[2] = SP_VACANT
    with _State(libstate, 8, 4, species, [2]) as st:
        assert _apply(libstate, st, []) == 0
        assert st.n_vac == 1
        assert st.species_array()[2] == SP_VACANT
        _check_invariants(st)


# ---------------------------------------------------------------------------
# Validation failures: rollback semantics
# ---------------------------------------------------------------------------


def test_wrong_before_rejects_with_no_mutation(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 6
    species[3] = SP_VACANT
    with _State(libstate, 6, 4, species, [3]) as st:
        # Action says "before=Vacant" at site 1, but site 1 currently has Ni.
        rc = _apply(libstate, st, [(1, SP_VACANT, SP_NI)])
        assert rc == EINVAL
        # Nothing changed.
        assert st.species_array() == species
        assert st.n_vac == 1
        assert st.vac_list_array() == [3]


def test_partial_validation_failure_no_partial_apply(libstate: ctypes.CDLL) -> None:
    """A valid action followed by an invalid one — neither should apply."""
    species = [SP_NI] * 6
    species[3] = SP_VACANT
    with _State(libstate, 6, 4, species, [3]) as st:
        rc = _apply(
            libstate,
            st,
            [
                (3, SP_VACANT, SP_NI),  # valid (would empty site 3)
                (5, SP_FE, SP_NI),  # invalid: site 5 is Ni, not Fe
            ],
        )
        assert rc == EINVAL
        assert st.species_array() == species  # untouched
        assert st.n_vac == 1


def test_duplicate_site_rejects(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 4
    with _State(libstate, 4, 2, species, []) as st:
        rc = _apply(
            libstate,
            st,
            [
                (1, SP_NI, SP_FE),
                (1, SP_FE, SP_CR),  # same site as previous
            ],
        )
        assert rc == EINVAL
        assert st.species_array() == species


def test_n_vac_overflow_rejects(libstate: ctypes.CDLL) -> None:
    """Adding a second vacancy when n_vac_max=1 must fail."""
    species = [SP_NI] * 4
    species[0] = SP_VACANT
    with _State(libstate, 4, 1, species, [0]) as st:
        rc = _apply(
            libstate,
            st,
            [
                (1, SP_NI, SP_VACANT),  # would make 2 vacancies; n_vac_max=1
            ],
        )
        assert rc == EINVAL
        assert st.species_array() == species
        assert st.n_vac == 1


# ---------------------------------------------------------------------------
# Single-site mutations
# ---------------------------------------------------------------------------


def test_atom_to_vacant_grows_vac_list(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 6
    with _State(libstate, 6, 4, species, []) as st:
        rc = _apply(libstate, st, [(2, SP_NI, SP_VACANT)])
        assert rc == 0
        assert st.n_vac == 1
        assert st.species_array()[2] == SP_VACANT
        assert st.vac_list_array() == [2]
        _check_invariants(st)


def test_vacant_to_atom_shrinks_vac_list(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 6
    species[2] = SP_VACANT
    with _State(libstate, 6, 4, species, [2]) as st:
        rc = _apply(libstate, st, [(2, SP_VACANT, SP_NI)])
        assert rc == 0
        assert st.n_vac == 0
        assert st.species_array()[2] == SP_NI
        assert st.vac_list_array() == []
        _check_invariants(st)


def test_atom_to_atom_no_vac_change(libstate: ctypes.CDLL) -> None:
    species = [SP_NI] * 6
    with _State(libstate, 6, 4, species, []) as st:
        rc = _apply(libstate, st, [(2, SP_NI, SP_FE)])
        assert rc == 0
        assert st.n_vac == 0
        assert st.species_array()[2] == SP_FE
        _check_invariants(st)


# ---------------------------------------------------------------------------
# Two-site hop (the most common pattern)
# ---------------------------------------------------------------------------


def test_simple_hop_preserves_n_vac(libstate: ctypes.CDLL) -> None:
    """Vacancy at site 2 hops to site 5 (Ni at 5 moves to 2)."""
    species = [SP_NI] * 8
    species[2] = SP_VACANT
    with _State(libstate, 8, 4, species, [2]) as st:
        rc = _apply(
            libstate,
            st,
            [
                (2, SP_VACANT, SP_NI),
                (5, SP_NI, SP_VACANT),
            ],
        )
        assert rc == 0
        assert st.n_vac == 1
        sp = st.species_array()
        assert sp[2] == SP_NI
        assert sp[5] == SP_VACANT
        assert st.vac_list_array() == [5]
        _check_invariants(st)


def test_hop_preserves_other_vacancies(libstate: ctypes.CDLL) -> None:
    """Two vacancies — one hops, the other untouched."""
    species = [SP_NI] * 10
    species[2] = SP_VACANT
    species[7] = SP_VACANT
    with _State(libstate, 10, 4, species, [2, 7]) as st:
        # Hop the vacancy at site 2 → site 4. Vacancy at 7 stays.
        rc = _apply(
            libstate,
            st,
            [
                (2, SP_VACANT, SP_NI),
                (4, SP_NI, SP_VACANT),
            ],
        )
        assert rc == 0
        assert st.n_vac == 2
        sp = st.species_array()
        assert sp[2] == SP_NI
        assert sp[4] == SP_VACANT
        assert sp[7] == SP_VACANT
        assert set(st.vac_list_array()) == {4, 7}
        _check_invariants(st)


# ---------------------------------------------------------------------------
# Three-site events — triple hop and concerted swap
# ---------------------------------------------------------------------------


def test_triple_hop_three_atom_shuffle(libstate: ctypes.CDLL) -> None:
    """Triple hop: vacancy at site 0; atoms at 1, 2 (Ni, Fe).
    After: site 0 ← Ni (was 1), site 1 ← Fe (was 2), site 2 ← Vacant.
    The vacancy effectively moved from 0 → 2. Species shuffle preserves
    atom identities along the chain."""
    species = [SP_VACANT, SP_NI, SP_FE, SP_NI, SP_NI]
    with _State(libstate, 5, 2, species, [0]) as st:
        rc = _apply(
            libstate,
            st,
            [
                (0, SP_VACANT, SP_NI),
                (1, SP_NI, SP_FE),
                (2, SP_FE, SP_VACANT),
            ],
        )
        assert rc == 0
        assert st.n_vac == 1
        assert st.species_array() == [SP_NI, SP_FE, SP_VACANT, SP_NI, SP_NI]
        assert st.vac_list_array() == [2]
        _check_invariants(st)


def test_subsurface_exchange_two_atom_swap(libstate: ctypes.CDLL) -> None:
    """A subsurface_exchange-like event: a Ni and an Fe swap positions across
    two layers (modelled here as just two arbitrary sites). No vacancy
    involved — pure species swap."""
    species = [SP_NI, SP_FE, SP_NI]
    with _State(libstate, 3, 2, species, []) as st:
        rc = _apply(
            libstate,
            st,
            [
                (0, SP_NI, SP_FE),
                (1, SP_FE, SP_NI),
            ],
        )
        assert rc == 0
        assert st.n_vac == 0
        assert st.species_array() == [SP_FE, SP_NI, SP_NI]
        _check_invariants(st)


# ---------------------------------------------------------------------------
# Vacancy-add and vacancy-remove (n_vac changes)
# ---------------------------------------------------------------------------


def test_creating_two_vacancies_in_one_apply(libstate: ctypes.CDLL) -> None:
    """A single apply call that turns two atoms into vacancies. n_vac grows
    by 2; vac_list and vac_idx_of must be coherent."""
    species = [SP_NI] * 8
    with _State(libstate, 8, 4, species, []) as st:
        rc = _apply(
            libstate,
            st,
            [
                (1, SP_NI, SP_VACANT),
                (5, SP_NI, SP_VACANT),
            ],
        )
        assert rc == 0
        assert st.n_vac == 2
        assert set(st.vac_list_array()) == {1, 5}
        _check_invariants(st)


def test_filling_vacancy_in_middle_of_list(libstate: ctypes.CDLL) -> None:
    """vac_list = [3, 7, 1]. Fill vacancy at site 7 (slot 1) — swap-last
    must move site 1 (slot 2) into slot 1; n_vac becomes 2."""
    species = [SP_NI] * 8
    species[3] = SP_VACANT
    species[7] = SP_VACANT
    species[1] = SP_VACANT
    with _State(libstate, 8, 4, species, [3, 7, 1]) as st:
        # Sanity: starting state is what we expect.
        assert st.vac_list_array() == [3, 7, 1]
        assert st.vac_idx_of_array()[7] == 1

        rc = _apply(libstate, st, [(7, SP_VACANT, SP_NI)])
        assert rc == 0
        assert st.n_vac == 2
        # vac_list now [3, 1] (swap-last moved site 1 into slot 1).
        assert set(st.vac_list_array()) == {3, 1}
        _check_invariants(st)


def test_combined_creation_and_removal(libstate: ctypes.CDLL) -> None:
    """One action removes a vacancy, another creates one — net n_vac unchanged.
    Removals must be processed before additions to avoid transient overflow
    when n_vac == n_vac_max at start."""
    species = [SP_NI] * 6
    species[3] = SP_VACANT
    # Set n_vac_max=1 so removals-first ordering matters: an addition before
    # the removal would temporarily push n_vac to 2.
    with _State(libstate, 6, 1, species, [3]) as st:
        rc = _apply(
            libstate,
            st,
            [
                (3, SP_VACANT, SP_NI),  # remove vacancy at 3
                (5, SP_NI, SP_VACANT),  # add vacancy at 5
            ],
        )
        assert rc == 0
        assert st.n_vac == 1
        assert st.species_array() == [SP_NI, SP_NI, SP_NI, SP_NI, SP_NI, SP_VACANT]
        assert st.vac_list_array() == [5]
        _check_invariants(st)


# ---------------------------------------------------------------------------
# Idempotency under repeated applies
# ---------------------------------------------------------------------------


def test_repeated_hops_invariants(libstate: ctypes.CDLL) -> None:
    """Run 50 hops in a chain. State should remain self-consistent
    after every step."""
    n = 12
    species = [SP_NI] * n
    species[0] = SP_VACANT
    with _State(libstate, n, 2, species, [0]) as st:
        cur = 0
        for _ in range(50):
            nxt = (cur + 1) % n
            # Skip if next is already vacant (shouldn't happen with 1 vac).
            assert st.species_array()[nxt] == SP_NI
            rc = _apply(
                libstate,
                st,
                [
                    (cur, SP_VACANT, SP_NI),
                    (nxt, SP_NI, SP_VACANT),
                ],
            )
            assert rc == 0
            _check_invariants(st)
            cur = nxt
        # After N hops we're somewhere on the chain with exactly 1 vacancy.
        assert st.n_vac == 1
