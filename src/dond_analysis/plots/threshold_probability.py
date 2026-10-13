from ..metrics import threshold_probability
from ._common import figure, risk_axis, smooth

TARGETS_DOLLARS = [39075, 190000, 280000, 450000]


def render(envelope, smoothing=1):
    fig, ax = figure("Approximate threshold probability (quantile estimate)", "P(cash ≥ target)")
    summaries = envelope["summaries"]
    x = risk_axis(ax, summaries)
    for target in TARGETS_DOLLARS:
        values = smooth(
            [threshold_probability(s["quantiles_cents"], target * 100) for s in summaries],
            smoothing,
        )
        ax.plot(
            x,
            values,
            marker="o" if len(summaries) == 1 else None,
            linestyle="None" if len(summaries) == 1 else "-",
            label=f"${target:,}",
        )
    ax.set_ylim(-0.02, 1.02)
    ax.legend(title="Target cash")
    return fig
