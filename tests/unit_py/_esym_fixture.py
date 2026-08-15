"""A deterministic synthetic v2 E_sym model + temp-spec builder for the C tests.

The Phase C parity / determinism tests need a *bakeable* ``esym_model.json`` on the
current (v2, 115-key) basis. The machine-local production artifact
(``.scratch/phaseC/esym_model_v1.json``) is a pre-v2 68-key model that
``emit_surrogate_tables`` now (correctly) refuses to bake, and the v2 refit is a
separate campaign leg. So the C-side tests build their own model here: the numbers
are meaningless physics but exercise every code path, and being *synthetic* is what
makes the parity test independent of any machine-local fit.

Everything is seeded and sorted — no ``hash()``, no set iteration — so the emitted
proclist.c stays byte-deterministic across ``PYTHONHASHSEED``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
NICR_SPEC = REPO_ROOT / "models" / "nicr_v2_scratch" / "nicr_v2_scratch.kmcspec.toml"


def synthetic_v2_model(seed: int = 20260815):  # noqa: ANN201 - EsymModel (lazy import)
    """A well-conditioned synthetic ``EsymModel`` on the pinned v2 basis.

    ``ainv`` is symmetric positive-definite so leverages are positive; ``sd`` is
    bounded away from zero so ``z = (phi-mu)/sd`` is finite. The Fe context range is
    ``(0, 0)`` — an all-NiCr-trained model — so any Fe context trips the OOD species
    trigger, exactly like the production bake will.
    """
    from pylatkmc.ingest.surrogate import ESYM_FEATURE_KEYS, H2FEATS, EsymModel

    n = len(ESYM_FEATURE_KEYS)
    nh = len(H2FEATS)
    rng = np.random.default_rng(seed)
    mu = rng.normal(0.0, 1.0, n)
    sd = np.abs(rng.normal(1.0, 0.2, n)) + 0.5
    w = rng.normal(0.0, 0.05, n)
    a = rng.normal(0.0, 1.0, (n, n))
    ainv = (a @ a.T) / n + 0.1 * np.eye(n)
    return EsymModel(
        model_version="E_sym_v2_ridge_sym2b3b_wf_SYNTHETIC",
        dE_model_version="H_sigma_v2_surfsplit_aug",
        alpha=30.0,
        feature_keys=ESYM_FEATURE_KEYS,
        mu=mu,
        sd=sd,
        ym=0.7,
        w=w,
        h2_feature_names=H2FEATS,
        h2_theta=rng.normal(0.0, 0.05, nh),
        ainv=ainv,
        lev_q75=0.11,
        lev_q90=0.21,
        lev_q95=0.29,
        tier0_nu0_hz=4.17e12,
        context_count_ranges={"N": (60, 130), "C": (1, 12), "E": (80, 180), "F": (0, 0)},
        ea_clamp=(0.05, 2.30),
        conditions="synthetic unit-test model (v2 115-key basis)",
        n_train=100,
    )


def write_v2_spec(tmp_dir: Path, seed: int = 20260815) -> Path:
    """Write ``{tmp_dir}/esym_v2.json`` + a nicr spec copy pointing at it.

    Returns the spec path. The copy keeps the real EventClass catalogue (so the
    measured channel (a) is still exercised) and only swaps the surrogate model;
    both paths are made absolute so the spec can live anywhere.
    """
    from pylatkmc.ingest.surrogate import save_model

    tmp_dir.mkdir(parents=True, exist_ok=True)
    model_json = tmp_dir / "esym_v2.json"
    save_model(synthetic_v2_model(seed), model_json)

    lines: list[str] = []
    for raw in NICR_SPEC.read_text().splitlines():
        if raw.startswith("event_class_table"):
            rel = raw.split("=", 1)[1].strip().strip('"')
            lines.append(f'event_class_table = "{(NICR_SPEC.parent / rel).resolve()}"')
        elif raw.startswith("surrogate_model"):
            lines.append(f'surrogate_model   = "{model_json}"')
        else:
            lines.append(raw)
    spec_path = tmp_dir / "nicr_v2_test.kmcspec.toml"
    spec_path.write_text("\n".join(lines) + "\n")
    return spec_path


def catalogue_available() -> bool:
    """True when the machine-local EventClass catalogue the nicr spec names exists."""
    for raw in NICR_SPEC.read_text().splitlines():
        if raw.startswith("event_class_table"):
            rel = raw.split("=", 1)[1].strip().strip('"')
            return (NICR_SPEC.parent / rel).resolve().exists()
    return False
