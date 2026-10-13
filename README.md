# Deal or No Deal: risk, utility, and simulated decisions

A reproducible research and portfolio project that studies how a player's utility function changes their decisions in the 26-case US version of *Deal or No Deal*. Rust generates complete game trajectories and evaluates agents; Python analyzes the summaries, draws figures, and collects optional utility surveys.

The central experiment compares constant relative risk aversion (CRRA) agents across an explicit risk-parameter grid. Each agent sees the same games and banker noise. A separate example uses a synthetic, monotone piecewise-linear utility function. Decisions compare an offer's utility with the expected utility of the remaining prizes; this is a behavioral rule, not a solution to the optimal stopping problem.

## Run the demo

Install [Rust](https://www.rust-lang.org/tools/install) and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run these commands from the repository root:

```bash
uv sync --locked
uv run dond demo
```

The pinned environment uses Rust **1.98.0** and Python **3.14.7**. The demo runs 1,000 games for 41 CRRA risk levels, plus the synthetic utility agent, with seed 102. It writes sweep and single-agent summaries, manifests, and five figures in PNG and SVG under `results/demo/`. Plots use a noninteractive backend unless `--show` is requested.

For the larger experiment:

```bash
uv run dond research
```

This preset runs 100,000 games for 201 CRRA risk levels and writes to `results/research/`. See [reproduction instructions](docs/reproduction.md) for resource costs, custom runs, and overwrite behavior.

## Research figures

![Winnings statistics across the CRRA risk grid](docs/assets/win_statistics.png)

*Research preset: payout statistics across the CRRA risk grid. The distributions summarize the modeled decision rule and banker, and should be interpreted within those assumptions.*

![Cash-out distribution by decision round](docs/assets/cash_out.png)

*Research preset: when agents accept the banker's offer or reach the reserved-case payout. Each risk level evaluates the same complete game trajectories.*

[Results and limitations](docs/results.md) records the run behind these figures and the measurements used to describe it.

## Analyze an existing run

```bash
uv run dond plot results/research/sweep.json --output results/research/figures
uv run dond analyze results/research/sweep.json --targets 39075 190000 280000 450000
```

Targets on the command line are **dollars**; simulator outputs store money in **integer cents**. The analysis reports approximate threshold probabilities and integrated CDF values from 1,001 quantile points. These summaries do not establish stochastic dominance.

## Optional utility survey

```bash
uv run dond survey --output personal/model.json --layers 3 --seed 102
uv run dond verify --model examples/synthetic-utility.json --seed 102
```

The survey creates a model from certainty-equivalent responses. Keep personal responses and models in the ignored `personal/` directory. The checked-in example is synthetic and contains no personal survey data.

## Project layout

| Path | Purpose |
| --- | --- |
| `crates/simulator/` | Rust game generation, utility policies, summaries, and `dond-sim` CLI |
| `src/dond_analysis/` | Python CLI, analysis, plots, and utility calibration |
| `examples/` | Explicit demo, research, and large-run presets; synthetic utility model |
| `tests/` | Python regression and integration checks |
| `docs/` | Methodology, reproduction instructions, results, and selected figures |
| `results/` | Ignored generated summaries, manifests, and figures |
| `personal/` | Ignored personal survey models and responses |

This release supersedes earlier unpublished scripts and results. The current engine includes all nine banker offers, pays the reserved case after nine declines, and uses the corrected integrated CDF calculation.

Read [methodology](docs/methodology.md) for the model and data conventions, [reproduction](docs/reproduction.md) to run experiments, and [contributing](CONTRIBUTING.md) for development checks. Code is available under the [MIT License](LICENSE); citation metadata is in [CITATION.cff](CITATION.cff).
