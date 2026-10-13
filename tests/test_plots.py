import matplotlib

matplotlib.use("Agg")
import pytest
from test_data import envelope

from dond_analysis.plots import render_all


@pytest.mark.parametrize("gamma", [None, 0.7])
def test_constant_single_distribution_all_figures(tmp_path, gamma):
    data = envelope()
    data["summaries"][0]["gamma"] = gamma
    if gamma is not None:
        data["config"].update(mode="sweep", gammas=[gamma], utility=None)
    paths = render_all(data, tmp_path)
    assert len(paths) == 10
    assert {p.suffix for p in paths} == {".png", ".svg"}
    assert all(p.stat().st_size > 100 for p in paths)


def test_smoothing_validation(tmp_path):
    with pytest.raises(ValueError, match="smoothing"):
        render_all(envelope(), tmp_path, smoothing=0)


def test_full_sweep_figures_remain_bounded():
    import copy

    import matplotlib.pyplot as plt

    from dond_analysis.plots import (
        cash_out,
        probability_density,
        threshold_probability,
        win_statistics,
    )

    data = envelope()
    template = data["summaries"][0]
    gammas = [i / 250 for i in range(201)]
    data["config"].update(mode="sweep", gammas=gammas, utility=None)
    data["summaries"] = []
    for gamma in gammas:
        summary = copy.deepcopy(template)
        summary["gamma"] = gamma
        summary["quantiles_cents"] = [i * 100 for i in range(1001)]
        data["summaries"].append(summary)
    for module in (cash_out, probability_density, threshold_probability, win_statistics):
        fig = module.render(data)
        try:
            if module is probability_density:
                assert len(fig.axes) == 9
            elif module is cash_out:
                assert fig.axes[0].images[0].get_array().shape == (201, 10)
                assert len(fig.axes[0].get_yticks()) <= 15
            elif module is threshold_probability:
                assert len(fig.axes[0].lines) == 4
                assert len(fig.axes[0].lines[0].get_xdata()) == 201
            else:
                assert len(fig.axes[0].lines) == 2
        finally:
            plt.close(fig)
