"""Shared constants + data access for the re-search campaign.

Protocol: RESEARCH_CAMPAIGN_PROTOCOL_DECISION_2026-07-22.md (onlattice_design).
Run under the pykmc_env venv. Nothing here touches the pyKMC MPI machinery.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

RUN_DIR = Path("/home/kerr/pykmc/production_NiCrFe/verify_fix_T500_1vac")
IMPL_DIR = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/impl")
CAMPAIGN_DIR = Path("/home/kerr/pykmc/pylatkmc/.scratch/phaseC/research_campaign")
STAMPED_PARQUET = IMPL_DIR / "catalogue_v3_qc_veto_stamped_impl.parquet"
FLUX_CSV = IMPL_DIR / "flux_restatement_impl.csv"
REF_PICKLE = RUN_DIR / "reference_table.pickle"
POTENTIAL = "/home/kerr/pykmc/Clusters/Research/NiFeCr_LKB2017.eam"
ARTN_INTERFACE = "/home/kerr/pykmc/artn-plugin/interface"

# Run conditions (memo "Conditions"; input.in of the production run)
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
T_REF_K = 500.0
GRAD_BAND_EV = 0.05

TYPE_ID = {"Cr": 1, "Ni": 2}   # alphabetical — pyKMC LAMMPS convention
MASSES = {"Cr": 51.996, "Ni": 58.6934}
PENDING = "pending_research"


def load_ref_table() -> pd.DataFrame:
    with open(REF_PICKLE, "rb") as f:
        return pickle.load(f)


def load_targets() -> pd.DataFrame:
    """The 81 pending classes joined with their flux, sorted flux-desc."""
    cat = pd.read_parquet(STAMPED_PARQUET)
    pend = cat[cat["nu0_pair_policy"] == PENDING].copy()
    flux = pd.read_csv(FLUX_CSV)[["class_id", "flux", "n_selected"]]
    pend = pend.merge(flux, on="class_id", how="left").sort_values(
        "flux", ascending=False, na_position="last"
    )
    pend["idx_ref"] = pend["source_idx_refs"].map(lambda v: int(np.asarray(v).ravel()[0]))
    return pend.reset_index(drop=True)
