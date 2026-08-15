"""Shared constants + data access for the NiFe re-search campaign (2026-08-15).

Adapted from research_campaign/rc_common.py (NiCr leg, 2026-07-22): the target
catalogue is the merged 60-run NiFe corpus (decision 3.4 of
NICRFE_INGEST_READINESS_2026-08-14.md), stamped all-pending on 2026-08-15, so
targets carry a per-class primary donor (run_tag, idx_ref) instead of a single
run's idx_ref. Run under the pykmc_env venv. Nothing here touches pyKMC MPI.
"""
from __future__ import annotations

import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

RUNS_ROOT = Path("/home/kerr/pykmc/production_NiCrFe/runs")
CAMPAIGN_DIR = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign_nife")
STAMPED_PARQUET = CAMPAIGN_DIR / "merged_v3_NiFe_stamped.parquet"
TARGETS_CSV = CAMPAIGN_DIR / "targets_nife.csv"
POTENTIAL = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
ARTN_INTERFACE = "/home/kerr/pykmc/artn-plugin/interface"

# Run conditions (uniform across the 60 NiFe runs — verified on the
# initial_config.xyz headers of T300_1vac / T500_5vac / T800_10vac)
CELL = np.diag([54.82057453, 54.82057453, 75.24])
RCUT = 8.5
EAM_CUTOFF = 5.6           # NiFeCr_LKB2017.eam header
PAD_RMAX = RCUT + EAM_CUTOFF
NOMINAL_A = 3.52
H = NOMINAL_A / 2.0
SNAP_TOL = 0.9             # occupancy criterion == projection gate snap_tol
SURF_TOL = 0.6             # surface-plane tolerance (~1/3 layer)
COLORING = "full"
D_MAX = 3
R_CTX_MIN = 3.6
GRAD_BAND_EV = 0.05

TYPE_ID = {"Fe": 1, "Ni": 2}   # alphabetical — pyKMC LAMMPS convention
MASSES = {"Fe": 55.845, "Ni": 58.6934}
PENDING = "pending_research"


@lru_cache(maxsize=12)
def load_ref_table(run_tag: str) -> pd.DataFrame:
    with open(RUNS_ROOT / run_tag / "reference_table.pickle", "rb") as f:
        return pickle.load(f)


def load_targets() -> pd.DataFrame:
    """Flux-ranked pending classes with the search member (run, idx_ref, Ea).

    The search member is the class member whose harvested barrier is closest to
    the class Ea_rep_eV (the graduation gate compares the re-search Ea against
    Ea_rep_eV, so the geometry searched should be the representative one; for
    the singleton majority this is simply the only member).
    """
    tg = pd.read_csv(TARGETS_CSV)
    cat = pd.read_parquet(
        STAMPED_PARQUET,
        columns=["class_id", "barriers_eV", "source_sim_paths"],
    ).set_index("class_id")

    runs, idxs, eas = [], [], []
    for cid, ea_rep in zip(tg["class_id"], tg["Ea_rep_eV"]):
        row = cat.loc[cid]
        bars = np.asarray(row["barriers_eV"], float)
        j = int(np.abs(bars - float(ea_rep)).argmin())
        run, idx = str(row["source_sim_paths"][j]).rsplit("#", 1)
        runs.append(run)
        idxs.append(int(idx))
        eas.append(float(bars[j]))
    tg["search_run"] = runs
    tg["search_idx"] = idxs
    tg["Ea_member_eV"] = eas
    return tg
