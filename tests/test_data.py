import copy
import json

import pytest

from dond_analysis.data import BOUNDS, load_results, validate_results


def envelope():
    return {
        "schema_version": 1,
        "model_version": "1.0.0",
        "currency_unit": "cents",
        "rng": "test",
        "config": {
            "mode": "single",
            "trials": 2,
            "seed": 1,
            "gammas": [],
            "utility": {
                "schema_version": 1,
                "name": "test",
                "points": [
                    {"cash_cents": 0, "utility": 0},
                    {"cash_cents": 100000000, "utility": 1},
                ],
            },
        },
        "summaries": [
            {
                "gamma": None,
                "agent": "utility",
                "sample_size": 2,
                "mean_cents": 100,
                "median_cents": 100,
                "std_dev_cents": 0,
                "quantile_probabilities": [i / 1000 for i in range(1001)],
                "quantiles_cents": [100] * 1001,
                "histogram": {"upper_bounds_cents": BOUNDS, "counts": [2] + [0] * 10},
                "cash_out_rounds": [0] * 9,
                "kept_case": 2,
            }
        ],
    }


def test_load_valid(tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps(envelope()))
    assert load_results(path)["summaries"][0]["sample_size"] == 2


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["summaries"][0]["histogram"]["counts"].__setitem__(0, 1),
        lambda d: d["summaries"][0]["quantiles_cents"].__setitem__(0, 200),
        lambda d: d["summaries"][0].__setitem__("mean_cents", float("nan")),
        lambda d: d["summaries"][0]["quantile_probabilities"].__setitem__(1, 0.4),
    ],
)
def test_invalid_results(mutation):
    data = copy.deepcopy(envelope())
    mutation(data)
    with pytest.raises(ValueError):
        validate_results(data)


def test_legacy_actionable():
    with pytest.raises(ValueError, match="rerun the simulator"):
        validate_results([])


def test_mode_grid_and_sample_size_validation():
    data = envelope()
    data["summaries"][0]["sample_size"] = 1
    with pytest.raises(ValueError, match="sample_size"):
        validate_results(data)
    data = envelope()
    data["config"].update(mode="sweep", gammas=[0.2], utility=None)
    with pytest.raises(ValueError, match="gamma"):
        validate_results(data)
    data["summaries"][0]["gamma"] = 0.2
    assert validate_results(data) is data
    data["config"]["gammas"] = [0.2, 0.1]
    with pytest.raises(ValueError, match="strictly increase"):
        validate_results(data)


def test_constants_match_rust_rules():
    import re
    from pathlib import Path

    from dond_analysis.data import PRIZES_CENTS

    rules = (Path(__file__).resolve().parents[1] / "crates/simulator/src/rules.rs").read_text()

    def array(name):
        body = re.search(rf"pub const {name}: \[u32; \d+\] = \[(.*?)\];", rules, re.S)[1]
        return [int(v.replace("_", "")) for v in re.findall(r"[\d_]+", body)]

    assert array("CASES") == PRIZES_CENTS
    assert array("HISTOGRAM_BOUNDS") == BOUNDS
