import pytest

from dond_analysis.metrics import integrated_cdf, threshold_probability


def test_equal_weight_metrics():
    assert threshold_probability([1, 3], 2) == 0.5
    assert threshold_probability([1, 3], 3) == 0.5
    assert integrated_cdf([1, 3], 2) == 0.5
    assert integrated_cdf([2, 2], 2) == 0


@pytest.mark.parametrize("values", [[], [float("nan")], [[1]]])
def test_bad_samples(values):
    with pytest.raises(ValueError):
        threshold_probability(values, 2)
