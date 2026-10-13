from ..metrics import integrated_cdf
from ._common import figure, risk_axis, smooth
from .threshold_probability import TARGETS_DOLLARS


def render(envelope, smoothing=1):
    fig, ax = figure(
        "Approximate integrated CDF (quantile estimate)", "Expected shortfall below target ($)"
    )
    summaries = envelope["summaries"]
    x = risk_axis(ax, summaries)
    for target in TARGETS_DOLLARS:
        values = smooth(
            [integrated_cdf(s["quantiles_cents"], target * 100) / 100 for s in summaries], smoothing
        )
        ax.plot(
            x,
            values,
            marker="o" if len(summaries) == 1 else None,
            linestyle="None" if len(summaries) == 1 else "-",
            label=f"${target:,}",
        )
    ax.legend(title="Target cash")
    return fig
