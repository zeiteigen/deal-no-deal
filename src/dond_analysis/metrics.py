"""Approximate distribution metrics from equally weighted quantiles."""

import numpy as np


def _samples(quantiles):
    values = np.asarray(quantiles, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("quantiles must be a nonempty finite one-dimensional sequence")
    return values


def threshold_probability(quantiles, target):
    """Approximate P(cash >= target), counting each quantile equally."""
    if not np.isfinite(target):
        raise ValueError("target must be finite")
    return float(np.mean(_samples(quantiles) >= target))


def integrated_cdf(quantiles, target):
    """Approximate integral of CDF up to target (expected shortfall in cents)."""
    if not np.isfinite(target):
        raise ValueError("target must be finite")
    return float(np.mean(np.maximum(target - _samples(quantiles), 0)))
