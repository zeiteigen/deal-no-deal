"""Seeded model predictions and optional participant decisions."""

import random

from ..utility import load_utility


def run_verification(model_path, seed, interactive=False):
    model = load_utility(model_path)
    rng = random.Random(seed)
    reports = []
    for _ in range(5):
        low, high = sorted(
            (rng.randint(model.cash[0], model.cash[-1]), rng.randint(model.cash[0], model.cash[-1]))
        )
        probability = rng.random()
        expected = probability * model.evaluate(low) + (1 - probability) * model.evaluate(high)
        ce = model.certainty_equivalent(expected)
        offer = round(max(model.cash[0], min(model.cash[-1], rng.uniform(0.9, 1.1) * ce)))
        offer_utility = model.evaluate(offer)
        predicted_take = offer_utility >= expected
        did_take = None
        print(
            f"Gamble: {probability:.1%} chance of ${low / 100:,.2f}, "
            f"otherwise ${high / 100:,.2f}; model CE ${ce / 100:,.2f}; "
            f"guaranteed offer ${offer / 100:,.2f}"
        )
        if interactive:
            while True:
                answer = input("Take the guaranteed offer? [yes/no]: ").strip().lower()
                if answer in ("yes", "y", "no", "n"):
                    did_take = answer in ("yes", "y")
                    break
                print("Please enter yes or no.")
            print(
                f"Model predicts {'take' if predicted_take else 'decline'}; "
                f"your decision {'agrees' if did_take == predicted_take else 'differs'}."
            )
        reports.append(
            {
                "low_cents": low,
                "high_cents": high,
                "probability_low": probability,
                "expected_utility": expected,
                "certainty_equivalent_cents": ce,
                "comparison_cents": offer,
                "comparison_utility": offer_utility,
                "predicted_take": predicted_take,
                "did_take": did_take,
            }
        )
    return reports
