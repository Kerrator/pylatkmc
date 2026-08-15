"""Refit the E_sym surrogate on the widened NiCr corpus — v2 basis (B2+B3 leg).

Run from the repo root with the pykmc_env venv active:
    python .scratch/phaseC/refit_esym_v2_2026-08-15.py

Produces esym_model_v2.json + esym_model_v2_fit_report.json next to this file.
Rulings 2026-08-15 (Stephen): (a) WILDCARD/OCC_ANY -> distinct "W"; (b) Fe -> distinct
"F"/CAT_F; (c) pooled ridge + mover-species dummies (no per-species heads).
"""

import json
import time
from pathlib import Path

from pylatkmc.ingest.event_class import read_catalogue_parquet
from pylatkmc.ingest.surrogate import (
    ESYM_FEATURE_KEYS,
    fit_esym_model,
    load_h2_theta_csv,
    save_model,
)

CORPUS = Path("/data/pylatkmc_ingest/sweep_catalogue_2026-08-14_full/merged_v3_NiCr.parquet")
H2_CSV = Path("/home/kerr/pykmc/onlattice_design/H_sigma_v2_theta_2026-07-21.csv")
OUT_JSON = Path(__file__).resolve().parent / "esym_model_v2.json"
OUT_REPORT = Path(__file__).resolve().parent / "esym_model_v2_fit_report.json"

CONDITIONS = (
    "CANON v3 merged NiCr corpus merged_v3_NiCr.parquet (2026-08-14 full campaign: 60 runs, "
    "70179 classes, 10699 quarantined excluded, 32 measured-stamped; curator vetoes carried). "
    "Basis v2: closed 115-key C/E/F/N/U/W alphabet (W = WILDCARD/OCC_ANY distinct, ruling "
    "2026-08-15a; F = Fe distinct, ruling b; mover_n_C/mover_n_F dummies, ruling c; pooled "
    "ridge). dE model: H_sigma_v2_surfsplit theta 2026-07-21 unchanged (18 feats); F/W "
    "contribute zero to dE_H by construction. NOTE train/serve skew: harvest-side W masking "
    "deflates N/C/E context counts vs the fully-observed runtime (errs toward over-flagging). "
    "Fit 2026-08-15, Linux box, pykmc_env py3.12."
)


def main() -> None:
    t0 = time.time()
    classes = read_catalogue_parquet(CORPUS)
    print(f"loaded {len(classes)} classes in {time.time() - t0:.0f}s", flush=True)
    h2_theta = load_h2_theta_csv(H2_CSV)

    t1 = time.time()
    model, report = fit_esym_model(classes, h2_theta, conditions=CONDITIONS)
    print(f"fit done in {time.time() - t1:.0f}s", flush=True)

    save_model(model, OUT_JSON)
    OUT_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=float) + "\n")

    print(f"model_version={model.model_version}  features={len(ESYM_FEATURE_KEYS)}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_REPORT}")
    print(json.dumps(report, indent=2, sort_keys=True, default=float))


if __name__ == "__main__":
    main()
