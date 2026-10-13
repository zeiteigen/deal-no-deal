"""Approximate quantile-based densities with bounded Scott-bandwidth KDE."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde

from ._common import label


def render(envelope, smoothing=1):
    # The KDE bandwidth smooths each density; `smoothing` applies only across γ in other figures.
    summaries = envelope["summaries"]
    selected = np.unique(np.linspace(0, len(summaries) - 1, min(9, len(summaries)), dtype=int))
    fig, axes = plt.subplots(
        len(selected),
        1,
        figsize=(9, max(4, len(selected) * 1.15)),
        sharex=True,
        constrained_layout=True,
        squeeze=False,
    )
    values = [np.asarray(summaries[i]["quantiles_cents"], dtype=float) / 100 for i in selected]
    low, high = min(q[0] for q in values), max(q[-1] for q in values)
    padding = max((high - low) * 0.04, 1)
    grid = np.linspace(max(0, low - padding), high + padding, 500)
    for row, index, q in zip(axes[:, 0], selected, values):
        if np.all(q == q[0]):
            row.axvline(q[0], color="C0", label="Point mass")
            row.text(0.98, 0.75, "Point mass", transform=row.transAxes, ha="right")
            row.set_ylim(0, 1)
        else:
            density = gaussian_kde(q, bw_method="scott")(grid)
            row.fill_between(grid, density, color="C0", alpha=0.4)
            row.plot(grid, density, color="C0")
        row.set_ylabel(label(summaries[index]), rotation=0, ha="right", va="center", fontsize=8)
        row.set_yticks([])
        row.spines[["top", "right"]].set_visible(False)
    axes[-1, 0].set_xlabel("Cash ($)")
    axes[0, 0].set_xlim(grid[0], grid[-1])
    fig.suptitle("Approximate quantile-based density (Scott KDE bandwidth)")
    return fig
