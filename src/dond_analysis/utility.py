"""Validated piecewise-linear utility and its leftmost inverse."""

import json
import math
from bisect import bisect_left, bisect_right
from pathlib import Path


class UtilityModel:
    def __init__(self, document):
        if (
            not isinstance(document, dict)
            or document.get("schema_version") != 1
            or not isinstance(document.get("name"), str)
            or not document["name"].strip()
        ):
            raise ValueError("utility requires schema_version=1 and a string name")
        points = document.get("points", [])
        if not isinstance(points, list) or len(points) < 2:
            raise ValueError("utility requires at least two points")
        self.cash = []
        self.utilities = []
        for point in points:
            if not isinstance(point, dict):
                raise ValueError("utility points must be objects")
            cash, utility = point.get("cash_cents"), point.get("utility")
            if isinstance(cash, bool) or not isinstance(cash, int) or not 0 <= cash <= 4294967295:
                raise ValueError(
                    "cash_cents must be integer cents in the uint32 range [0, 4294967295]"
                )
            if (
                isinstance(utility, bool)
                or not isinstance(utility, (int, float))
                or not math.isfinite(utility)
            ):
                raise ValueError("utility must be finite")
            if self.cash and cash <= self.cash[-1]:
                raise ValueError(
                    "cash_cents must be strictly increasing; "
                    "duplicate cash points must be merged or removed"
                )
            if self.utilities and utility < self.utilities[-1]:
                raise ValueError("utility must be nondecreasing")
            self.cash.append(cash)
            self.utilities.append(float(utility))
        self.document = document

    def evaluate(self, cash_cents):
        if not math.isfinite(cash_cents) or not self.cash[0] <= cash_cents <= self.cash[-1]:
            raise ValueError("cash is outside the utility model domain")
        i = min(bisect_right(self.cash, cash_cents) - 1, len(self.cash) - 2)
        fraction = (cash_cents - self.cash[i]) / (self.cash[i + 1] - self.cash[i])
        return self.utilities[i] + fraction * (self.utilities[i + 1] - self.utilities[i])

    def certainty_equivalent(self, utility):
        if not math.isfinite(utility) or not self.utilities[0] <= utility <= self.utilities[-1]:
            raise ValueError("target utility is outside the utility model range")
        i = bisect_left(self.utilities, utility)
        if self.utilities[i] == utility:
            return float(self.cash[i])
        fraction = (utility - self.utilities[i - 1]) / (self.utilities[i] - self.utilities[i - 1])
        return self.cash[i - 1] + fraction * (self.cash[i] - self.cash[i - 1])


def load_utility(path):
    return UtilityModel(json.loads(Path(path).read_text()))
