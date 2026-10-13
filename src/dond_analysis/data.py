"""Read and validate versioned simulator results."""

import json
import math
from pathlib import Path

from .utility import UtilityModel

# Mirrors CASES and HISTOGRAM_BOUNDS in crates/simulator/src/rules.rs; tests check they agree.
PRIZES_CENTS = [
    1,
    100,
    500,
    1_000,
    2_500,
    5_000,
    7_500,
    10_000,
    20_000,
    30_000,
    40_000,
    50_000,
    75_000,
    100_000,
    500_000,
    1_000_000,
    2_500_000,
    5_000_000,
    7_500_000,
    10_000_000,
    20_000_000,
    30_000_000,
    40_000_000,
    50_000_000,
    75_000_000,
    100_000_000,
]
BOUNDS = [
    50000,
    100000,
    1000000,
    5000000,
    10000000,
    20000000,
    30000000,
    50000000,
    75000000,
    100000000,
]


def _integer(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def validate_results(document):
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError(
            "Unsupported or legacy results: rerun the simulator to produce schema_version=1 JSON"
        )
    if document.get("model_version") != "1.0.0" or document.get("currency_unit") != "cents":
        raise ValueError("Results require model_version='1.0.0' and currency_unit='cents'")
    if not isinstance(document.get("rng"), str):
        raise ValueError("rng must name the random-number generator")
    config = document.get("config", {})
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    if config.get("mode") not in ("sweep", "single"):
        raise ValueError("config.mode must be sweep or single")
    _integer(config.get("trials"), "trials", 1)
    _integer(config.get("seed"), "seed")
    if not isinstance(config.get("gammas"), list):
        raise ValueError("gammas must be a list")
    for gamma in config["gammas"]:
        _finite(gamma, "gamma")
    if "utility" not in config:
        raise ValueError("config.utility must be null or a utility model")
    if config["utility"] is not None:
        model = UtilityModel(config["utility"])
    if config["mode"] == "sweep":
        gammas = config["gammas"]
        if (
            not gammas
            or any(not -10 <= g < 1 for g in gammas)
            or any(a >= b for a, b in zip(gammas, gammas[1:]))
        ):
            raise ValueError("sweep gammas must strictly increase and lie in [-10, 1)")
        if config["utility"] is not None:
            raise ValueError("sweep utility must be null")
    elif config["utility"] is None or config["gammas"]:
        raise ValueError("single mode requires a utility model and an empty gamma grid")
    elif model.cash[0] != 0 or model.cash[-1] < 100_000_000:
        raise ValueError("simulation utility domain must cover 0 through 100000000 cents")
    summaries = document.get("summaries")
    if not isinstance(summaries, list) or not summaries:
        raise ValueError("summaries must be a nonempty list")
    expected_gammas = config["gammas"] if config["mode"] == "sweep" else [None]
    if [s.get("gamma") if isinstance(s, dict) else None for s in summaries] != expected_gammas:
        raise ValueError("summary gamma values must match the mode and configured gamma grid")
    for summary in summaries:
        if not isinstance(summary, dict):
            raise ValueError("summaries must contain objects")
        if "gamma" not in summary:
            raise ValueError("summary.gamma must be a number or null")
        if summary.get("gamma") is not None:
            _finite(summary["gamma"], "gamma")
        if not isinstance(summary.get("agent"), str):
            raise ValueError("agent must be a string")
        n = summary.get("sample_size")
        _integer(n, "sample_size", 1)
        if n != config["trials"]:
            raise ValueError("sample_size must equal config.trials")
        for key in ("mean_cents", "median_cents", "std_dev_cents"):
            _finite(summary.get(key), key)
        if summary["std_dev_cents"] < 0:
            raise ValueError("std_dev_cents cannot be negative")
        probabilities = summary.get("quantile_probabilities", [])
        quantiles = summary.get("quantiles_cents", [])
        if not isinstance(probabilities, list) or not isinstance(quantiles, list):
            raise ValueError("quantile probabilities and values must be lists")
        if len(probabilities) != 1001 or len(quantiles) != 1001:
            raise ValueError("exactly 1001 quantile probabilities and values are required")
        for i, probability in enumerate(probabilities):
            _finite(probability, "quantile probability")
            if not math.isclose(probability, i / 1000, abs_tol=1e-12):
                raise ValueError("quantile probabilities must evenly cover 0 through 1")
        for value in quantiles:
            _integer(value, "quantile cents")
        if quantiles != sorted(quantiles):
            raise ValueError("quantile values must be sorted")
        histogram = summary.get("histogram", {})
        if not isinstance(histogram, dict):
            raise ValueError("histogram must be an object")
        if histogram.get("upper_bounds_cents") != BOUNDS:
            raise ValueError("histogram upper bounds do not match schema v1")
        for name, counts, length in (
            ("histogram", histogram.get("counts", []), 11),
            ("cash_out_rounds", summary.get("cash_out_rounds", []), 9),
        ):
            if not isinstance(counts, list) or len(counts) != length:
                raise ValueError(f"{name} requires {length} counts")
            for count in counts:
                _integer(count, name)
        _integer(summary.get("kept_case"), "kept_case")
        if (
            sum(histogram["counts"]) != n
            or sum(summary["cash_out_rounds"]) + summary["kept_case"] != n
        ):
            raise ValueError("histogram and decision counts must sum to sample_size")
    return document


def load_results(path):
    return validate_results(json.loads(Path(path).read_text()))
