"""Generate reproducible figures from validated simulation summaries."""

from pathlib import Path

import matplotlib.pyplot as plt

from ..data import validate_results
from . import cash_out, integrated_cdf, probability_density, threshold_probability, win_statistics


def render_all(envelope, output_dir, show=False, smoothing=1):
    validate_results(envelope)
    if isinstance(smoothing, bool) or not isinstance(smoothing, int) or smoothing < 1:
        raise ValueError("smoothing must be a positive integer; 1 preserves raw values")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for module in (
        win_statistics,
        probability_density,
        cash_out,
        threshold_probability,
        integrated_cdf,
    ):
        fig = module.render(envelope, smoothing=smoothing)
        try:
            for extension in ("png", "svg"):
                path = output / f"{module.__name__.rsplit('.', 1)[-1]}.{extension}"
                fig.savefig(path)
                paths.append(path)
            if show:
                plt.show()
        finally:
            plt.close(fig)
    return paths
