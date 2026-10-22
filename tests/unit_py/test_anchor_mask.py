"""The anchor-species mask and the vacancy-only step loop (large-system-scaling WP4a).

Codegen emits ``PYLATKMC_ANCHOR_SPECIES_MASK`` into proclist.h: the species at
which ``touchup_a`` can enrol anything. When that is the vacancy alone,
``kmc_step_once`` touches up only the vacant sites (``active_filter_rescan_
vacancies``) instead of every surface site and every 1NN of a vacancy. A mask
missing a species would silently drop that species' enrolments, so:

- both emitters' ``anchor_species`` (v0.3 decision tree, v2 pattern tables) and
  the proclist.h block they feed;
- every COMMITTED proclist.h (CI links them without regenerating) carries the
  mask, and it agrees with its own proclist.c's touchup_a;
- the step loop takes the vacancy-only path for a vacancy-only mask, and the
  full rescan for any other mask and for an older proclist.h without one.

The active-list order itself is tested in test_active_filter.py. ctypes and
compile level, no MPI launch; skips without cc.
"""

from __future__ import annotations

import ctypes
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from pylatkmc.codegen import _PROCLIST_H_TEMPLATE, _anchor_mask_define, generate
from pylatkmc.decision_tree import anchor_species as v03_anchor_species
from pylatkmc.loader import load
from pylatkmc.pattern_codegen import anchor_species as v2_anchor_species
from pylatkmc.processes import Action, Condition, CoordOffset, Process
from pylatkmc.rate_expression import KB_EV_PER_K

REPO_ROOT = Path(__file__).resolve().parents[2]  # pylatkmc/
CORE = REPO_ROOT / "runtime" / "src" / "core"
IO = REPO_ROOT / "runtime" / "src" / "io"
SPECIES = ["Vacant", "Ni", "Fe", "Cr"]  # events_base.h code order

ANCHOR = CoordOffset(code="NC_ANCHOR")
PX = CoordOffset(code="NC_NN1_PX")


def _process(name: str, conditions: tuple[Condition, ...], actions: tuple[Action, ...]) -> Process:
    return Process(
        name=name,
        family_id="test",
        Ea_eV=0.5,
        rate_constant=1.0e13,
        conditions=conditions,
        actions=actions,
    )


def _hop(name: str = "hop") -> Process:
    """A vacancy-anchored 1NN hop."""
    return _process(
        name,
        (Condition(coord=ANCHOR, species="Vacant"), Condition(coord=PX, species="Ni")),
        (
            Action(coord=ANCHOR, before="Vacant", after="Ni"),
            Action(coord=PX, before="Ni", after="Vacant"),
        ),
    )


def _dissolve(species: str) -> Process:
    """An atom-anchored dissolution (the anchor's own species leaves)."""
    return _process(
        f"diss_{species.lower()}",
        (Condition(coord=ANCHOR, species=species),),
        (Action(coord=ANCHOR, before=species, after="Vacant"),),
    )


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def test_v03_anchor_species() -> None:
    assert v03_anchor_species([]) == []
    assert v03_anchor_species([_hop("a"), _hop("b")]) == ["Vacant"]
    assert v03_anchor_species([_hop(), _dissolve("Ni"), _dissolve("Cr")]) == [
        "Cr",
        "Ni",
        "Vacant",
    ]
    # No anchor-site Condition: touchup_a can enrol it at a site of any
    # species (here it walks the +x neighbour only), so no mask can be safe.
    unanchored = _process(
        "unanchored",
        (Condition(coord=PX, species="Vacant"),),
        (Action(coord=PX, before="Vacant", after="Ni"),),
    )
    assert v03_anchor_species([_hop(), unanchored]) is None


def test_v2_anchor_species() -> None:
    from pylatkmc.translator_v2 import DeltaRow, LatticePattern

    def pattern(name: str, anchor: str) -> LatticePattern:
        return LatticePattern(
            class_id=name,
            name=name,
            anchor_species=anchor,
            delta=(DeltaRow((0, 0, 0), anchor, "Vacant" if anchor != "Vacant" else "Ni"),),
            context=(),
            orientation_ops=(0,),
            prefactor_Hz=1.0e13,
            Ea_eV=0.5,
            mover_species=("Ni",),
            n_members=1,
            depth_kind=0,
            depth_param=0,
        )

    assert v2_anchor_species([]) == []
    assert v2_anchor_species([pattern("a", "Vacant"), pattern("b", "Vacant")]) == ["Vacant"]
    # Runtime code order (events_base.h), the order of v2_pattern_bucket_begin.
    mixed = [pattern("c", "Cr"), pattern("a", "Vacant"), pattern("n", "Ni")]
    assert v2_anchor_species(mixed) == ["Vacant", "Ni", "Cr"]


def _mask_of(header: str) -> str:
    m = re.search(r"^#define PYLATKMC_ANCHOR_SPECIES_MASK (.+)$", header, re.M)
    assert m, "proclist.h has no PYLATKMC_ANCHOR_SPECIES_MASK"
    return m.group(1)


def test_mask_define_names_the_bits_in_species_order() -> None:
    assert _mask_of(_anchor_mask_define(["Vacant"], SPECIES)) == "(1u << SP_VACANT)"
    assert _mask_of(_anchor_mask_define(["Cr", "Ni", "Vacant"], SPECIES)) == (
        "((1u << SP_VACANT) | (1u << SP_NI) | (1u << SP_CR))"
    )
    assert _mask_of(_anchor_mask_define([], SPECIES)) == "0u"
    assert _mask_of(_anchor_mask_define(None, SPECIES)) == "(~0u)"


def test_generate_emits_the_mask(tmp_path: Path) -> None:
    """ni_example (vendored catalogue, regenerates anywhere): vacancy hops only."""
    spec_path = REPO_ROOT / "models" / "ni_example" / "ni_example.kmcspec.toml"
    generate(load(spec_path), tmp_path, spec_path=spec_path)
    assert _mask_of((tmp_path / "proclist.h").read_text()) == "(1u << SP_VACANT)"


# ---------------------------------------------------------------------------
# Committed proclists: the mask agrees with the touchup it describes
# ---------------------------------------------------------------------------


def _touchup_anchor_species(src: str) -> set[str]:
    """The species at which a generated touchup_a can enrol anything, read
    from the generated C: the v2 per-species pattern buckets, or the case
    labels of the v0.3 tree's top-level switch on the anchor's species."""
    m = re.search(r"v2_pattern_bucket_begin\[\d+\] = \{([\d,]+)\};", src)
    if m:
        begin = [int(b) for b in m.group(1).split(",")]
        return {SPECIES[c].upper() for c in range(len(begin) - 1) if begin[c + 1] > begin[c]}
    start = re.search(r"^void touchup_a\(.*\{$", src, re.M)
    assert start, "no touchup_a definition"
    body = src[start.end() :].splitlines()[1:]
    body = body[: body.index("}")]
    top = [line for line in body if re.match(r"    \S", line)]
    assert top == ["    switch (st->species[site]) {", "    }"], (
        "touchup_a is not one switch on the anchor's species; extend this parser"
    )
    return set(re.findall(r"^        case SP_([A-Z]+):$", "\n".join(body), re.M))


def test_committed_proclists_carry_a_mask_that_matches_their_touchup() -> None:
    headers = sorted((REPO_ROOT / "models").glob("*/generated/proclist.h"))
    assert len(headers) >= 5
    vacancy_only = []
    for h in headers:
        mask = _mask_of(h.read_text())
        assert "~0u" not in mask, f"{h}: every committed model anchors on known species"
        named = set(re.findall(r"SP_([A-Z]+)", mask))
        assert named == _touchup_anchor_species((h.parent / "proclist.c").read_text()), (
            f"{h}: the mask disagrees with touchup_a (regenerate the model)"
        )
        vacancy_only.append(named == {"VACANT"})
    # Both paths of the step loop are exercised by the committed models.
    assert any(vacancy_only) and not all(vacancy_only)


# ---------------------------------------------------------------------------
# The step loop: which sites kmc_step_once touches up
# ---------------------------------------------------------------------------

#: A one-proc fake proclist whose touchup_a logs every call, and a harness that
#: runs one kmc_step_once on an n-site chain. Every chain site has fewer than
#: 12 neighbours, so the full rescan lists every site (all static).
_LOGGING_PROCLIST_C = r"""
#include <string.h>

#include "proclist.h"
#include "events_base.h"
#include "kmc.h"

static const RateConst rate_table[1] = { { 1.0e13, 0.5, 0, 0 } };

static HopOutcome noop_apply(struct State *st, const struct Lattice *lat, int site)
{
    (void)st; (void)lat; (void)site;
    return (HopOutcome){ -1, -1 };
}

static const ApplyFn apply_table[1] = { noop_apply };
const int32_t pylatkmc_n_procs = 1;
const RateConst *const pylatkmc_rate_table = rate_table;
const ApplyFn   *const pylatkmc_apply_table = apply_table;

#define LOG_CAP 64
static int32_t g_log[LOG_CAP];
static int32_t g_n_log;

void touchup_a(const struct Lattice *lat, const struct State *st,
               struct AvailSites *as, int site)
{
    (void)lat;
    if (g_n_log < LOG_CAP) g_log[g_n_log] = site;
    ++g_n_log;
    if (st->species[site] == SP_VACANT) avail_sites_add(as, 0, site);
}

int pylatkmc_test_touchups(int32_t n, const int32_t *vac, int32_t n_vac, int32_t *out)
{
    if (n < 2 || n > LOG_CAP || n_vac < 1) return -1000;
    int32_t off[LOG_CAP + 1], idx[2 * LOG_CAP], m = 0;
    for (int32_t s = 0; s < n; ++s) {
        off[s] = m;
        if (s > 0) idx[m++] = s - 1;
        if (s < n - 1) idx[m++] = s + 1;
    }
    off[n] = m;
    Lattice lat;
    memset(&lat, 0, sizeof lat);
    lat.n_sites = n;
    lat.nn1_offsets = off;
    lat.nn1_indices = idx;
    State st;
    if (state_alloc(&st, n, n_vac) != 0) return -1001;
    for (int32_t s = 0; s < n; ++s) st.species[s] = SP_NI;
    for (int32_t v = 0; v < n_vac; ++v) {
        st.species[vac[v]] = SP_VACANT;
        st.vac_list[v] = vac[v];
        st.vac_idx_of[vac[v]] = v;
    }
    st.n_vac = n_vac;
    AvailSites *as = NULL;
    ActiveFilter *af = NULL;
    if (avail_sites_alloc(&as, 1, n) != 0 || active_filter_alloc(&af, n, 12) != 0
        || active_filter_compute_static(af, &lat) != 0)
        return -1002;
    avail_sites_set_rate(as, 0, rateconst_eval(rate_table[0], 500.0, 0.0));
    Rng rng;
    rng_seed(&rng, 42, 0);
    KmcRunConfig cfg;
    memset(&cfg, 0, sizeof cfg);
    KmcContext ctx = { .lat = &lat, .st = &st, .as = as, .af = af, .rng = &rng,
                       .cfg = &cfg, .temperature_K = 500.0 };
    g_n_log = 0;
    int rc = kmc_step_once(&ctx, NULL, NULL, NULL, NULL);
    for (int32_t i = 0; i < g_n_log && i < LOG_CAP; ++i) out[i] = g_log[i];
    active_filter_free(af);
    avail_sites_free(as);
    state_free(&st);
    return rc == 0 ? g_n_log : rc;
}
"""


def _touchup_sites(tmp: Path, extra_defines: str, vac: list[int], n: int = 10) -> list[int]:
    """Build kmc.c against a proclist.h with ``extra_defines`` and return the
    sites one kmc_step_once touches up."""
    if shutil.which("cc") is None:
        pytest.skip("cc not on PATH")
    tmp.mkdir()
    (tmp / "proclist.h").write_text(
        _PROCLIST_H_TEMPLATE.format(
            spec_name="anchor_mask_test", kb_ev_per_k=KB_EV_PER_K, extra_defines=extra_defines
        )
    )
    (tmp / "fake_proclist.c").write_text(_LOGGING_PROCLIST_C)
    lib_path = tmp / ("libstep.dylib" if sys.platform == "darwin" else "libstep.so")
    srcs = [tmp / "fake_proclist.c"]
    srcs += [CORE / f for f in ("kmc.c", "avail_sites.c", "active_filter.c", "state.c")]
    srcs += [CORE / "state_actions.c", CORE / "rng.c"]
    srcs += [IO / f for f in ("xyz_writer.c", "pykmc_out.c", "phasec_out.c")]
    cmd = ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC", "-shared"]
    cmd += ["-I", str(tmp), "-I", str(CORE), "-I", str(IO)]
    cmd += [str(s) for s in srcs] + ["-o", str(lib_path), "-lm"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.fail(f"build failed:\n{res.stderr}")
    lib = ctypes.CDLL(str(lib_path))
    i32p = ctypes.POINTER(ctypes.c_int32)
    lib.pylatkmc_test_touchups.argtypes = [ctypes.c_int32, i32p, ctypes.c_int32, i32p]
    lib.pylatkmc_test_touchups.restype = ctypes.c_int
    out = (ctypes.c_int32 * 64)()
    k = lib.pylatkmc_test_touchups(n, (ctypes.c_int32 * len(vac))(*vac), len(vac), out)
    assert k >= 0, f"kmc_step_once harness failed: {k}"
    return list(out[:k])


def test_step_loop_touches_up_only_the_vacancies_for_a_vacancy_only_mask(
    tmp_path: Path,
) -> None:
    vac = [6, 2, 5]  # vac_list order; all three are static (chain), so ascending
    vacant = _anchor_mask_define(["Vacant"], SPECIES)
    assert _touchup_sites(tmp_path / "vacant", vacant, vac) == [2, 5, 6]
    # No anchoring species at all (an empty catalogue): nothing to skip either.
    assert _touchup_sites(tmp_path / "none", _anchor_mask_define([], SPECIES), vac) == [2, 5, 6]


def test_step_loop_rescans_every_active_site_otherwise(tmp_path: Path) -> None:
    vac = [6, 2, 5]
    every = list(range(10))
    assert (
        _touchup_sites(tmp_path / "occupied", _anchor_mask_define(["Vacant", "Ni"], SPECIES), vac)
        == every
    )
    assert _touchup_sites(tmp_path / "any", _anchor_mask_define(None, SPECIES), vac) == every
    # A proclist.h generated before the mask existed: the full rescan, as before.
    assert _touchup_sites(tmp_path / "legacy", "", vac) == every
