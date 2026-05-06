"""Ctypes-driven tests for the C `avail_sites` data structure (M-C.1, M-C.2, M-C.3).

The C source under test is `runtime/src/core/avail_sites.{h,c}` — a port of
kmos's Fortran `avail_sites(proc, k, switch)` array (kmos-main/kmos/
fortran_src/base.mpy:88-302) with O(1) swap-last add/del semantics.

We compile the .c into a shared library at test-collection time and exercise
its API via ctypes, covering:

* add/del round-trip invariants (slot_of[] consistent with site_at[])
* random-workload stress: 1000 ops over (proc, site) space, no leaks
* BKL `select`: empty, single-proc, multi-proc with known cumulative weights
* clear() between rebuilds restores fresh state without re-allocation
"""
from __future__ import annotations

import ctypes
import errno
import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

# errno values differ across platforms (e.g. ENODATA = 61 on Linux, 96 on macOS).
ENODATA = -errno.ENODATA
EINVAL = -errno.EINVAL

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
SRC = REPO_ROOT / "runtime" / "src" / "core" / "avail_sites.c"
HDR = REPO_ROOT / "runtime" / "src" / "core" / "avail_sites.h"


def _have_cc() -> bool:
    return shutil.which("cc") is not None


@pytest.fixture(scope="module")
def libavail(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    """Compile avail_sites.c into a shared lib once per test session."""
    if not _have_cc():
        pytest.skip("cc not on PATH")
    if not SRC.is_file():
        pytest.fail(f"missing source: {SRC}")
    if not HDR.is_file():
        pytest.fail(f"missing header: {HDR}")

    builddir = tmp_path_factory.mktemp("avail_sites_lib")
    libname = "libavail_sites.dylib" if os.uname().sysname == "Darwin" else "libavail_sites.so"
    libpath = builddir / libname

    # -DNDEBUG matches release builds: the assert()s in add/del compile to
    # nothing, leaving the `if (...) return;` runtime guards as the only
    # safety net. Debug builds would abort on misuse — that's by design,
    # but we test the release-mode no-op fallback here.
    cmd = [
        "cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-O2", "-DNDEBUG", "-fPIC", "-shared",
        "-I", str(HDR.parent),
        str(SRC),
        "-o", str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(
            f"avail_sites.c failed to compile:\n"
            f"  cmd: {' '.join(cmd)}\n"
            f"  stderr:\n{res.stderr}"
        )

    lib = ctypes.CDLL(str(libpath))

    # AvailSites is opaque; we treat its handle as a void*.
    lib.avail_sites_alloc.restype = ctypes.c_int
    lib.avail_sites_alloc.argtypes = [
        ctypes.POINTER(ctypes.c_void_p), ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_free.restype = None
    lib.avail_sites_free.argtypes = [ctypes.c_void_p]
    lib.avail_sites_set_rate.restype = None
    lib.avail_sites_set_rate.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_double]
    lib.avail_sites_clear.restype = None
    lib.avail_sites_clear.argtypes = [ctypes.c_void_p]
    lib.avail_sites_add.restype = None
    lib.avail_sites_add.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_del.restype = None
    lib.avail_sites_del.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_refresh_cum_rates.restype = None
    lib.avail_sites_refresh_cum_rates.argtypes = [ctypes.c_void_p]
    lib.avail_sites_r_tot.restype = ctypes.c_double
    lib.avail_sites_r_tot.argtypes = [ctypes.c_void_p]
    lib.avail_sites_select.restype = ctypes.c_int
    lib.avail_sites_select.argtypes = [
        ctypes.c_void_p, ctypes.c_double,
        ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32)]
    lib.avail_sites_n_procs.restype = ctypes.c_int32
    lib.avail_sites_n_procs.argtypes = [ctypes.c_void_p]
    lib.avail_sites_n_sites.restype = ctypes.c_int32
    lib.avail_sites_n_sites.argtypes = [ctypes.c_void_p]
    lib.avail_sites_count.restype = ctypes.c_int32
    lib.avail_sites_count.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.avail_sites_is_enrolled.restype = ctypes.c_int32
    lib.avail_sites_is_enrolled.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_site_at.restype = ctypes.c_int32
    lib.avail_sites_site_at.argtypes = [
        ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
    lib.avail_sites_rate.restype = ctypes.c_double
    lib.avail_sites_rate.argtypes = [ctypes.c_void_p, ctypes.c_int32]
    lib.avail_sites_cum_rate.restype = ctypes.c_double
    lib.avail_sites_cum_rate.argtypes = [ctypes.c_void_p, ctypes.c_int32]

    return lib


# ---------------------------------------------------------------------------
# Small helper to wrap the C handle in a Python object with auto-free
# ---------------------------------------------------------------------------


class _AvailSites:
    """Thin RAII wrapper so tests can `with _AvailSites(lib, np, ns) as a:`."""

    def __init__(self, lib: ctypes.CDLL, n_procs: int, n_sites: int) -> None:
        self.lib = lib
        h = ctypes.c_void_p()
        rc = lib.avail_sites_alloc(ctypes.byref(h), n_procs, n_sites)
        if rc != 0:
            raise RuntimeError(f"avail_sites_alloc failed: rc={rc}")
        self.h = h

    def __enter__(self) -> "_AvailSites":
        return self

    def __exit__(self, *exc) -> None:  # noqa: ANN001
        if self.h:
            self.lib.avail_sites_free(self.h)
            self.h = None

    # Forwarding methods.
    def set_rate(self, p: int, r: float) -> None: self.lib.avail_sites_set_rate(self.h, p, r)
    def clear(self) -> None: self.lib.avail_sites_clear(self.h)
    def add(self, p: int, s: int) -> None: self.lib.avail_sites_add(self.h, p, s)
    def delete(self, p: int, s: int) -> None: self.lib.avail_sites_del(self.h, p, s)
    def refresh(self) -> None: self.lib.avail_sites_refresh_cum_rates(self.h)
    def r_tot(self) -> float: return float(self.lib.avail_sites_r_tot(self.h))
    def select(self, target: float) -> tuple[int, int, int]:
        p = ctypes.c_int32(); s = ctypes.c_int32()
        rc = self.lib.avail_sites_select(self.h, target, ctypes.byref(p), ctypes.byref(s))
        return rc, p.value, s.value
    def count(self, p: int) -> int: return int(self.lib.avail_sites_count(self.h, p))
    def enrolled(self, p: int, s: int) -> int:
        return int(self.lib.avail_sites_is_enrolled(self.h, p, s))
    def site_at(self, p: int, k: int) -> int:
        return int(self.lib.avail_sites_site_at(self.h, p, k))
    def rate(self, p: int) -> float: return float(self.lib.avail_sites_rate(self.h, p))
    def cum_rate(self, p: int) -> float: return float(self.lib.avail_sites_cum_rate(self.h, p))


# ---------------------------------------------------------------------------
# Basic API: alloc / introspection / clean teardown
# ---------------------------------------------------------------------------


def test_alloc_then_free(libavail: ctypes.CDLL) -> None:
    """Round-trip alloc/free does not leak; introspection matches inputs."""
    h = ctypes.c_void_p()
    assert libavail.avail_sites_alloc(ctypes.byref(h), 4, 16) == 0
    assert h.value is not None
    assert libavail.avail_sites_n_procs(h) == 4
    assert libavail.avail_sites_n_sites(h) == 16
    libavail.avail_sites_free(h)


def test_alloc_rejects_invalid(libavail: ctypes.CDLL) -> None:
    h = ctypes.c_void_p()
    assert libavail.avail_sites_alloc(ctypes.byref(h), 0, 16) == EINVAL
    assert libavail.avail_sites_alloc(ctypes.byref(h), 4, 0) == EINVAL


# ---------------------------------------------------------------------------
# add/del round-trip invariants
# ---------------------------------------------------------------------------


def test_add_then_enrolled(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 3, 8) as a:
        # Initially nothing enrolled.
        for p in range(3):
            for s in range(8):
                assert a.enrolled(p, s) == 0
            assert a.count(p) == 0

        # Add (proc=1, site=4).
        a.add(1, 4)
        assert a.enrolled(1, 4) == 1
        assert a.count(1) == 1
        assert a.site_at(1, 0) == 4
        # Other procs untouched.
        assert a.enrolled(0, 4) == 0
        assert a.enrolled(2, 4) == 0


def test_del_then_not_enrolled(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 2, 8) as a:
        a.add(0, 3)
        assert a.enrolled(0, 3) == 1
        a.delete(0, 3)
        assert a.enrolled(0, 3) == 0
        assert a.count(0) == 0
        assert a.site_at(0, 0) == -1   # out-of-range read returns -1


def test_swap_last_preserves_other_sites(libavail: ctypes.CDLL) -> None:
    """Deleting a non-last entry must move the last entry into the freed slot
    *and* update slot_of[] for the moved site."""
    with _AvailSites(libavail, 1, 16) as a:
        for s in (1, 4, 9, 11):
            a.add(0, s)
        assert a.count(0) == 4

        # Delete site=4 (which is at slot 1). The last site (11) should move
        # into slot 1; site 9 stays in slot 2; site 1 in slot 0.
        a.delete(0, 4)
        assert a.count(0) == 3
        assert a.enrolled(0, 4) == 0
        assert a.enrolled(0, 1) == 1
        assert a.enrolled(0, 9) == 1
        assert a.enrolled(0, 11) == 1
        # Now delete the moved entry — slot_of[11] must be the freed slot 1.
        a.delete(0, 11)
        assert a.count(0) == 2
        # Remaining entries are 1 and 9 in some order in slots 0 and 1.
        remaining = {a.site_at(0, k) for k in range(2)}
        assert remaining == {1, 9}


def test_double_add_is_noop(libavail: ctypes.CDLL) -> None:
    """Re-adding an already-enrolled (proc, site) doesn't double-count.
    (Asserts in debug; runtime guard prevents corruption either way.)"""
    with _AvailSites(libavail, 1, 8) as a:
        a.add(0, 5)
        a.add(0, 5)   # silent no-op (we built without -DDEBUG)
        assert a.count(0) == 1
        assert a.enrolled(0, 5) == 1


def test_double_del_is_noop(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 1, 8) as a:
        a.add(0, 5)
        a.delete(0, 5)
        a.delete(0, 5)   # silent no-op
        assert a.count(0) == 0
        assert a.enrolled(0, 5) == 0


# ---------------------------------------------------------------------------
# Random-workload stress: 1000 ops, half deletes, all invariants hold
# ---------------------------------------------------------------------------


def test_random_workload_invariants(libavail: ctypes.CDLL) -> None:
    """Run 1000 random ops; reference set tracks ground truth."""
    rng = random.Random(20260506)
    n_procs, n_sites = 8, 64
    truth: set[tuple[int, int]] = set()

    with _AvailSites(libavail, n_procs, n_sites) as a:
        for _ in range(1000):
            p = rng.randrange(n_procs)
            s = rng.randrange(n_sites)
            if (p, s) in truth:
                a.delete(p, s)
                truth.discard((p, s))
            else:
                a.add(p, s)
                truth.add((p, s))

        # After all ops, every (p, s) in truth must be enrolled, and every
        # other pair must not be.
        for p in range(n_procs):
            expected_count = sum(1 for q, _ in truth if q == p)
            assert a.count(p) == expected_count, f"count mismatch for proc {p}"
            for s in range(n_sites):
                expected = 1 if (p, s) in truth else 0
                assert a.enrolled(p, s) == expected, (
                    f"enrolled mismatch at (proc={p}, site={s}): truth={expected}"
                )
            # Dense list contains exactly the enrolled sites for proc p.
            seen = {a.site_at(p, k) for k in range(a.count(p))}
            expected_sites = {s for q, s in truth if q == p}
            assert seen == expected_sites, f"dense list mismatch for proc {p}"


def test_clear_resets_to_empty(libavail: ctypes.CDLL) -> None:
    """clear() restores fresh state without re-allocating."""
    with _AvailSites(libavail, 4, 16) as a:
        for p in range(4):
            for s in range(8):
                a.add(p, s)
        for p in range(4):
            assert a.count(p) == 8

        a.clear()
        for p in range(4):
            assert a.count(p) == 0
            for s in range(16):
                assert a.enrolled(p, s) == 0

        # And we can re-populate after a clear.
        a.add(2, 13)
        assert a.enrolled(2, 13) == 1
        assert a.count(2) == 1


# ---------------------------------------------------------------------------
# Cumulative rates + BKL selection
# ---------------------------------------------------------------------------


def test_cum_rates_match_per_proc_product(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 3, 8) as a:
        a.set_rate(0, 1.0)
        a.set_rate(1, 2.5)
        a.set_rate(2, 0.5)

        # 2 sites for proc 0, 3 for proc 1, 1 for proc 2.
        for s in (0, 1):       a.add(0, s)
        for s in (2, 3, 4):    a.add(1, s)
        for s in (5,):         a.add(2, s)

        a.refresh()
        # Expected: [1.0*2, +2.5*3, +0.5*1] = [2.0, 9.5, 10.0]
        assert a.cum_rate(0) == pytest.approx(2.0)
        assert a.cum_rate(1) == pytest.approx(9.5)
        assert a.cum_rate(2) == pytest.approx(10.0)
        assert a.r_tot()    == pytest.approx(10.0)


def test_select_returns_correct_proc_and_valid_site(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 3, 16) as a:
        a.set_rate(0, 1.0); a.set_rate(1, 2.0); a.set_rate(2, 4.0)
        a.add(0, 1); a.add(0, 7)              # proc 0: 2 sites, weight 2.0
        a.add(1, 3); a.add(1, 11); a.add(1, 12)  # proc 1: 3 sites, weight 6.0
        a.add(2, 9)                            # proc 2: 1 site,  weight 4.0
        a.refresh()
        # cum: [2, 8, 12]; r_tot=12

        # target = 0.5 → proc 0
        rc, p, s = a.select(0.5)
        assert rc == 0 and p == 0 and s in {1, 7}

        # target = 1.5 → still proc 0
        rc, p, s = a.select(1.5)
        assert rc == 0 and p == 0 and s in {1, 7}

        # target = 2.5 → proc 1
        rc, p, s = a.select(2.5)
        assert rc == 0 and p == 1 and s in {3, 11, 12}

        # target = 7.999 → still proc 1 (cum[1]=8)
        rc, p, s = a.select(7.999)
        assert rc == 0 and p == 1 and s in {3, 11, 12}

        # target = 8.5 → proc 2
        rc, p, s = a.select(8.5)
        assert rc == 0 and p == 2 and s == 9


def test_select_distribution_uniform_within_proc(libavail: ctypes.CDLL) -> None:
    """Across many uniform-random targets, sites of one proc should get
    selected roughly proportionally to their (rate × n_sites) weight."""
    with _AvailSites(libavail, 2, 32) as a:
        a.set_rate(0, 1.0); a.set_rate(1, 1.0)
        for s in range(4):  a.add(0, s)        # proc 0: 4 sites
        for s in range(8):  a.add(1, s + 8)    # proc 1: 8 sites
        a.refresh()
        # cum=[4, 12]; r_tot=12

        rng = random.Random(42)
        n_p0, n_p1 = 0, 0
        N = 12_000
        for _ in range(N):
            t = rng.random() * 12.0
            rc, p, _ = a.select(t)
            assert rc == 0
            if p == 0: n_p0 += 1
            else:      n_p1 += 1

        # Expected: n_p0/N ≈ 1/3, n_p1/N ≈ 2/3. With N=12000 the binomial
        # 1-σ is sqrt(N*p*q) ≈ 51, so 5σ ≈ 250. Use 300 as the slop.
        assert abs(n_p0 - N // 3) < 300
        assert abs(n_p1 - 2 * N // 3) < 300


def test_select_empty_returns_enodata(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 2, 8) as a:
        a.set_rate(0, 1.0); a.set_rate(1, 1.0)
        a.refresh()
        rc, _, _ = a.select(0.0)
        assert rc == ENODATA


def test_select_after_clear_returns_enodata(libavail: ctypes.CDLL) -> None:
    """Clear should drop the population to empty so r_tot becomes 0 even
    if the rate constants stayed set."""
    with _AvailSites(libavail, 2, 8) as a:
        a.set_rate(0, 1.0); a.set_rate(1, 1.0)
        a.add(0, 0); a.add(1, 0)
        a.refresh()
        assert a.r_tot() > 0.0
        a.clear()
        a.refresh()
        assert a.r_tot() == 0.0
        rc, _, _ = a.select(0.0)
        assert rc == ENODATA


def test_set_rate_negative_ignored(libavail: ctypes.CDLL) -> None:
    with _AvailSites(libavail, 2, 8) as a:
        a.set_rate(0, 1.0)
        a.set_rate(0, -3.0)   # rejected; rate stays 1.0
        assert a.rate(0) == pytest.approx(1.0)


def test_select_skips_zero_rate_proc(libavail: ctypes.CDLL) -> None:
    """A proc with rate 0 has zero weight in cum_rates but may still hold
    enrolled sites. The selector should never pick it."""
    with _AvailSites(libavail, 3, 16) as a:
        a.set_rate(0, 1.0); a.set_rate(1, 0.0); a.set_rate(2, 1.0)
        a.add(0, 0); a.add(1, 1); a.add(2, 2)
        a.refresh()
        # cum=[1, 1, 2]; r_tot=2; proc 1 has zero-width band so should never
        # be selected.
        rng = random.Random(7)
        for _ in range(200):
            t = rng.random() * a.r_tot()
            rc, p, _ = a.select(t)
            assert rc == 0
            assert p != 1, "selector picked a zero-rate proc"
