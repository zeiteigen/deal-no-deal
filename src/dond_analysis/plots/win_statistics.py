import numpy as np

from ._common import figure, risk_axis, smooth


def render(envelope, smoothing=1):
    fig, ax = figure("Win statistics", "Cash ($)")
    summaries = envelope["summaries"]
    x = risk_axis(ax, summaries)
    means = smooth([s["mean_cents"] / 100 for s in summaries], smoothing)
    medians = smooth([s["median_cents"] / 100 for s in summaries], smoothing)
    q = smooth(np.asarray([s["quantiles_cents"] for s in summaries]) / 100, smoothing)
    if len(summaries) == 1:
        ax.vlines(
            0, q[0, 100], q[0, 900], color="C0", linewidth=3, label="10–90% quantile interval"
        )
        ax.vlines(
            0, q[0, 250], q[0, 750], color="C0", linewidth=9, label="25–75% quantile interval"
        )
        ax.scatter(x, means, label="Mean", zorder=3)
        ax.scatter(x, medians, marker="x", label="Median", zorder=4)
    else:
        ax.fill_between(
            x, q[:, 100], q[:, 900], color="C0", alpha=0.12, label="10–90% quantile band"
        )
        ax.fill_between(
            x, q[:, 250], q[:, 750], color="C0", alpha=0.25, label="25–75% quantile band"
        )
        ax.plot(x, means, label="Mean")
        ax.plot(x, medians, label="Median", linestyle="--")
    ax.legend()
    return fig
