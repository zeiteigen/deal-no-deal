"""Figure construction and risk-axis helpers."""

import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import uniform_filter1d


def figure(title, ylabel):
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    return fig, ax


def label(summary):
    gamma = summary["gamma"]
    return summary["agent"] + (f" (γ={gamma:g})" if gamma is not None else "")


def risk_axis(ax, summaries):
    if len(summaries) == 1:
        ax.set_xticks([0], [label(summaries[0])])
        ax.set_xlim(-0.5, 0.5)
        ax.set_xlabel("Agent")
        return np.array([0.0])
    ax.set_xlabel("Risk parameter γ")
    return np.asarray([s["gamma"] for s in summaries], dtype=float)


def smooth(values, smoothing):
    values = np.asarray(values, dtype=float)
    return (
        uniform_filter1d(values, size=smoothing, mode="nearest", axis=0)
        if smoothing > 1
        else values
    )
