import numpy as np

from ._common import figure, label


def render(envelope, smoothing=1):
    fig, ax = figure("Cash-out decisions", "Risk parameter γ")
    summaries = envelope["summaries"]
    values = np.array([s["cash_out_rounds"] + [s["kept_case"]] for s in summaries], dtype=float)
    values /= np.array([s["sample_size"] for s in summaries])[:, None]
    image = ax.imshow(values, aspect="auto", origin="lower", vmin=0, vmax=1, cmap="viridis")
    ticks = np.unique(np.linspace(0, len(summaries) - 1, min(15, len(summaries)), dtype=int))
    ax.set_yticks(
        ticks,
        [
            f"{summaries[i]['gamma']:g}"
            if summaries[i]["gamma"] is not None
            else label(summaries[i])
            for i in ticks
        ],
    )
    ax.set_xticks(range(10), [str(i) for i in range(1, 10)] + ["Kept case"])
    ax.set_xlabel("Decision round")
    ax.grid(False)
    fig.colorbar(image, ax=ax, label="Fraction of trials")
    return fig
