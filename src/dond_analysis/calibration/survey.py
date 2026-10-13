"""Elicit certainty equivalents with recursively subdivided fair gambles."""

import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from ..utility import UtilityModel


def _parse_cents(answer, low, high, points):
    """Return integer cents for a valid answer, or an explanation of the problem."""
    try:
        dollars = float(answer.strip().replace("$", "").replace(",", ""))
    except ValueError:
        return None, "Enter a dollar amount such as 1234.56"
    if not math.isfinite(dollars) or not low / 100 <= dollars <= high / 100:
        return None, f"Enter an amount between ${low / 100:,.2f} and ${high / 100:,.2f}"
    cash = round(dollars * 100)
    if cash in points:
        return None, "Choose an amount strictly between the two outcomes"
    return cash, None


def _ask_certainty_equivalent(low, high, points):
    while True:
        answer = input(
            f"50/50 gamble: ${low / 100:,.2f} or ${high / 100:,.2f}. "
            "Enter your certainty equivalent in dollars: "
        )
        cash, problem = _parse_cents(answer, low, high, points)
        if problem is None:
            return cash
        print(problem)


def run_survey(output, layers, seed, force=False):
    if isinstance(layers, bool) or not isinstance(layers, int) or layers < 1:
        raise ValueError("layers must be an integer >= 1")
    path = Path(output)
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; choose another path or use --force")
    rng = random.Random(seed)
    points = {0: 0.0, 100_000_000: 1.0}
    intervals = [(0, 100_000_000, 0.0, 1.0)]
    responses = []
    for layer in range(layers):
        rng.shuffle(intervals)
        next_intervals = []
        for low, high, u_low, u_high in intervals:
            if high - low < 2:
                raise ValueError(
                    "No distinct integer certainty equivalent remains; "
                    "reduce layers or adjust earlier answers"
                )
            cash = _ask_certainty_equivalent(low, high, points)
            utility = (u_low + u_high) / 2
            points[cash] = utility
            responses.append(
                {
                    "layer": layer + 1,
                    "low_cents": low,
                    "high_cents": high,
                    "certainty_equivalent_cents": cash,
                }
            )
            next_intervals.extend(((low, cash, u_low, utility), (cash, high, utility, u_high)))
        intervals = next_intervals
    document = {
        "schema_version": 1,
        "name": "Calibrated utility",
        "points": [
            {"cash_cents": cash, "utility": utility} for cash, utility in sorted(points.items())
        ],
        "session": {
            "seed": seed,
            "layers": layers,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "responses": responses,
        },
    }
    UtilityModel(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if force else "x") as handle:
        json.dump(document, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return document
