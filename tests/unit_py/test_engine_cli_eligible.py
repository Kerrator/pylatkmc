import json

import numpy as np

from pylatkmc.cli import main


def test_eligible_command_lists_processes(tmp_path, capsys, monkeypatch):
    # Build a tiny spec dir with a committed catalogue.json and a packed .kmcinit,
    # then drive `pylatkmc-gen eligible`.
    import pathlib
    import sys

    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    from _engine_fixtures import pack_kmcinit as _pack_kmcinit

    spec_dir = tmp_path / "m"
    (spec_dir / "generated").mkdir(parents=True)
    spec = spec_dir / "m.kmcspec.toml"
    spec.write_text(
        'name = "m"\n'
        'lattice = "fcc"\n'
        'species = ["Vacant", "Ni", "Fe", "Cr"]\n'
        '[[shells]]\nname = "nn1"\ncutoff_mult = 1.05\n'
        '[[key.axes]]\nname = "mover_species"\nkind = "enum"\nmax = 3\nskip_vacant = true\n'
        "[rate_data]\n"
        'primary = "p.csv"\n'
        'temperature_K = 500.0\n'
        "k0_Hz = 1.0e13\n",
        encoding="utf-8",
    )
    catalogue = [
        {
            "name": "demo_hop",
            "family_id": "surface_1NN_inplane",
            "Ea_eV": 0.5,
            "rate_constant": 1.0e9,
            "conditions": [
                {"coord": {"code": "NC_ANCHOR"}, "species": "Vacant"},
                {"coord": {"code": "NC_NN1_PX"}, "species": "Ni"},
            ],
            "actions": [
                {"coord": {"code": "NC_ANCHOR"}, "before": "Vacant", "after": "Ni"},
                {"coord": {"code": "NC_NN1_PX"}, "before": "Ni", "after": "Vacant"},
            ],
            "shell_conditions": [],
            "bystanders": [],
        }
    ]
    (spec_dir / "generated" / "catalogue.json").write_text(json.dumps(catalogue))
    kmcinit = _pack_kmcinit(
        spec_dir,
        positions=np.array([[0.0, 0, 0], [1.0, 0, 0], [2.0, 0, 0]], np.float32),
        nn1_offsets=np.array([0, 1, 3, 4], np.int32),
        nn1_indices=np.array([1, 0, 2, 1], np.int32),
        nn2_offsets=np.array([0, 0, 0, 0], np.int32),
        nn2_indices=np.array([], np.int32),
        layer_index=np.zeros(3, np.int8),
        site_class=np.zeros(3, np.uint8),
        initial_species=np.array([0, 1, 1], np.uint8),
        nn_dist=1.0, cell=(100.0, 100.0, 100.0), n_layers=1,
    )
    rc = main(["eligible", str(spec), "--kmcinit", str(kmcinit), "--site", "0"])
    assert rc == 0
    assert "demo_hop" in capsys.readouterr().out
