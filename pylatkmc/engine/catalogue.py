"""Load, compile, and export the Process catalogue for the Python engine.

The catalogue is the SAME ``list[Process]`` the C codegen consumes. Source priority:
explicit ``--family-csv`` → the spec's ``family_table`` (off-repo on most machines) →
the committed ``generated/catalogue.json``. ``compile_catalogue`` turns Process objects
into an index-based form (species/code integers) for fast eligibility checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pylatkmc.engine.coords import CODE_INDEX
from pylatkmc.loader import load
from pylatkmc.processes import Process
from pylatkmc.translator import load_family_rate_table, translate_all

SPECIES_STUB: int = 255
_SHELL_KIND = {"1nn": 0, "2nn": 1}


def _generated_dir(spec_path: Path) -> Path:
    return spec_path.parent / "generated"


def _resolve_family_csv(spec_path: Path, family_csv: str | Path | None) -> Path | None:
    spec = load(spec_path)
    if family_csv is not None:
        cand = Path(family_csv)
        if not cand.is_absolute():
            cand = (spec_path.parent / cand).resolve()
        return cand if cand.exists() else None
    ft = spec.rate_data.family_table
    if ft is None:
        return None
    cand = Path(ft)
    if not cand.is_absolute():
        cand = (spec_path.parent / cand).resolve()
    return cand if cand.exists() else None


def _translate_from_csv(spec_path: Path, family_csv: Path) -> list[Process]:
    spec = load(spec_path)
    rows = load_family_rate_table(family_csv)
    return translate_all(
        rows,
        k0_Hz=spec.rate_data.k0_Hz,
        T_K=spec.rate_data.temperature_K,
    )


def load_catalogue(
    spec_path: str | Path, family_csv: str | Path | None = None
) -> list[Process]:
    spec_path = Path(spec_path).resolve()
    csv = _resolve_family_csv(spec_path, family_csv)
    if csv is not None:
        return _translate_from_csv(spec_path, csv)
    cat_json = _generated_dir(spec_path) / "catalogue.json"
    if cat_json.exists():
        raw = cat_json.read_text(encoding="utf-8")
        import json

        return [Process.model_validate(obj) for obj in json.loads(raw)]
    raise FileNotFoundError(
        "No catalogue source: family CSV did not resolve and "
        f"{cat_json} is absent. Run `pylatkmc-gen export-catalogue {spec_path}` "
        "on a checkout where the family CSV resolves, and commit the JSON."
    )


def export_catalogue(
    spec_path: str | Path,
    out_path: str | Path | None = None,
    family_csv: str | Path | None = None,
) -> Path:
    import json

    spec_path = Path(spec_path).resolve()
    csv = _resolve_family_csv(spec_path, family_csv)
    if csv is None:
        raise FileNotFoundError(
            "export-catalogue requires the family CSV to resolve "
            "(spec.rate_data.family_table or --family-csv)."
        )
    processes = _translate_from_csv(spec_path, csv)
    out = Path(out_path) if out_path else _generated_dir(spec_path) / "catalogue.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = [p.model_dump(mode="json") for p in processes]
    out.write_text(json.dumps(payload, indent=0), encoding="utf-8")
    return out


@dataclass(frozen=True)
class CompiledProcess:
    name: str
    family_id: str
    Ea_eV: float
    rate: float
    anchor_species: int
    conds: tuple[tuple[int, int], ...]
    shells: tuple[tuple[int, int, int, int], ...]
    actions: tuple[tuple[int, int, int], ...]
    v_from_code: int
    v_to_code: int


def compile_catalogue(processes: list[Process], species: list[str]) -> list[CompiledProcess]:
    sidx = {name: i for i, name in enumerate(species)}
    out: list[CompiledProcess] = []
    for p in processes:
        if not isinstance(p.rate_constant, (int, float)):
            raise ValueError(
                f"Process {p.name!r} has a non-scalar rate_constant "
                f"({p.rate_constant!r}); the Python engine only supports v2 float rates."
            )
        conds = tuple((CODE_INDEX[c.coord.code], sidx[c.species]) for c in p.conditions)
        shells = tuple(
            (CODE_INDEX[s.coord.code], _SHELL_KIND[s.shell], sidx[s.species], s.count)
            for s in p.shell_conditions
        )
        actions = tuple(
            (CODE_INDEX[a.coord.code], sidx[a.before], sidx[a.after]) for a in p.actions
        )
        anchor_species = next(
            (sidx[c.species] for c in p.conditions if c.coord.code == "NC_ANCHOR"),
            SPECIES_STUB,
        )
        vacant = sidx["Vacant"]
        v_from = next(
            (CODE_INDEX[a.coord.code] for a in p.actions if sidx[a.before] == vacant),
            CODE_INDEX["NC_ANCHOR"],
        )
        v_to = next(
            (CODE_INDEX[a.coord.code] for a in p.actions if sidx[a.after] == vacant),
            CODE_INDEX["NC_ANCHOR"],
        )
        out.append(
            CompiledProcess(
                name=p.name,
                family_id=p.family_id,
                Ea_eV=p.Ea_eV,
                rate=float(p.rate_constant),
                anchor_species=anchor_species,
                conds=conds,
                shells=shells,
                actions=actions,
                v_from_code=v_from,
                v_to_code=v_to,
            )
        )
    return out
