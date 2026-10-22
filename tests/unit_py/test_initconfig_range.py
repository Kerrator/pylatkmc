"""Ctypes tests for `initconfig_load`'s header range checks (`runtime/src/io/initconfig.c`).

Site indices and CSR offsets are int32 in the runtime. A `.kmcinit` header
whose `n_sites` / `nn1_count` / `nn2_count` exceeds INT32_MAX used to be cast
straight to int32, so 2^32 + 8 sites silently became an 8-site lattice
(large-system-scaling/06). It must now be refused with -EOVERFLOW. The files
here are tiny: only the header claims the huge count, nothing is allocated.
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
RUNTIME = REPO_ROOT / "runtime" / "src"
SOURCES = [
    RUNTIME / "io" / "initconfig.c",
    RUNTIME / "core" / "kmcfmt.c",
    RUNTIME / "core" / "json_mini.c",
    RUNTIME / "core" / "state.c",
    RUNTIME / "core" / "lattice.c",
    RUNTIME / "core" / "coord_codes.c",
]
N_SITES = 8
INT32_MAX = 2**31 - 1


@pytest.fixture(scope="module")
def libinit(tmp_path_factory: pytest.TempPathFactory) -> ctypes.CDLL:
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    builddir = tmp_path_factory.mktemp("initconfig_lib")
    libname = "libinitconfig.dylib" if os.uname().sysname == "Darwin" else "libinitconfig.so"
    libpath = builddir / libname
    cmd = [
        "cc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-fPIC",
        "-shared",
        "-I",
        str(RUNTIME / "core"),
        "-I",
        str(RUNTIME / "io"),
        *map(str, SOURCES),
        "-lm",
        "-o",
        str(libpath),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"initconfig.c + deps failed to compile:\n{res.stderr}")
    lib = ctypes.CDLL(str(libpath))
    lib.initconfig_load.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_int32,
    ]
    lib.initconfig_load.restype = ctypes.c_int
    lib.lattice_free.argtypes = [ctypes.c_void_p]
    lib.lattice_free.restype = None
    lib.state_free.argtypes = [ctypes.c_void_p]
    lib.state_free.restype = None
    return lib


def _write_kmcinit(path: Path, *, n_sites: int, nn1_count: int = 0, nn2_count: int = 0) -> Path:
    """A valid 8-site, edge-free .kmcinit whose HEADER claims the given counts
    (same layout as tools/build_initial_config.py / tools/kmcfmt.py)."""
    header = {
        "version": 1,
        "n_sites": n_sites,
        "n_layers": 1,
        "cell": [10.0, 10.0, 10.0],
        "nn_dist": 2.49,
        "nn1_count": nn1_count,
        "nn2_count": nn2_count,
    }
    raw = json.dumps(header, separators=(",", ":"), sort_keys=True).encode()
    raw += b"\x00" * ((4 - len(raw) % 4) % 4)
    n = N_SITES
    payload = b"".join(
        [
            struct.pack("<I", 1),  # payload version
            struct.pack(f"<{3 * n}f", *([1.0] * (3 * n))),  # positions
            struct.pack(f"<{n + 1}i", *([0] * (n + 1))),  # nn1_offsets (no edges)
            struct.pack(f"<{n + 1}i", *([0] * (n + 1))),  # nn2_offsets (no edges)
            bytes(n),  # layer_index
            bytes(n),  # site_class
            bytes([0] + [1] * (n - 1)),  # initial_species: 1 vacancy + Ni
        ]
    )
    path.write_bytes(b"KMCICv01" + struct.pack("<I", len(raw)) + raw + payload)
    return path


def _load(lib: ctypes.CDLL, path: Path) -> tuple[int, int]:
    """initconfig_load into opaque Lattice/State buffers; returns (rc, n_sites)."""
    lat = ctypes.create_string_buffer(4096)
    st = ctypes.create_string_buffer(4096)
    rc = lib.initconfig_load(str(path).encode(), lat, st, 0)
    n_sites = ctypes.c_int32.from_buffer(lat).value  # Lattice.n_sites is the first field
    if rc == 0:
        lib.lattice_free(lat)
        lib.state_free(st)
    return rc, n_sites


def test_valid_header_loads(libinit: ctypes.CDLL, tmp_path: Path) -> None:
    rc, n = _load(libinit, _write_kmcinit(tmp_path / "ok.kmcinit", n_sites=N_SITES))
    assert (rc, n) == (0, N_SITES)


@pytest.mark.parametrize(
    "field, value",
    [
        ("n_sites", 2**32 + N_SITES),  # truncates to 8 == the payload: loaded silently before
        ("n_sites", INT32_MAX + 1),  # truncates to INT32_MIN
        ("nn1_count", 2**32),  # truncates to 0 == the CSR edge count
        ("nn2_count", 2**32),
    ],
)
def test_header_counts_above_int32_are_refused(
    libinit: ctypes.CDLL, tmp_path: Path, field: str, value: int
) -> None:
    counts = {"n_sites": N_SITES, field: value}
    rc, _ = _load(libinit, _write_kmcinit(tmp_path / "big.kmcinit", **counts))
    assert rc == -errno.EOVERFLOW
