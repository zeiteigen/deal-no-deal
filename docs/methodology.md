# Methodology

## Question and scope

The simulator asks how a utility-based acceptance rule changes payouts and cash-out timing under a specified *Deal or No Deal* game and banker model. It compares CRRA agents and a monotone piecewise-linear utility agent on common game trajectories. It does not estimate the behavior of actual contestants or learn a banker from broadcast data.

## Game and banker

The 26 US prizes, in dollars, are:

```text
0.01, 1, 5, 10, 25, 50, 75, 100, 200, 300, 400, 500, 750,
1,000, 5,000, 10,000, 25,000, 50,000, 75,000, 100,000,
200,000, 300,000, 400,000, 500,000, 750,000, 1,000,000
```

Each game shuffles these prizes. The final shuffled case is reserved as the player's case; the other cases are opened in order. Nine rounds open `6, 5, 4, 3, 2, 1, 1, 1, 1` cases, leaving two unopened cases after the last round. Every round has a banker offer, including the ninth. An agent that rejects all nine offers receives the prize in the reserved case.

The banker multiplies the arithmetic mean of the remaining prizes by a round coefficient and an independent uniform noise factor from `[0.95, 1.05]`. The round coefficients are:

```text
0.10, 0.19, 0.29, 0.42, 0.55, 0.68, 0.87, 0.95, 1.01
```

Money is stored as integer cents. Each calculated offer is truncated to integer cents. This banker is an explicit modeling assumption, so conclusions depend on these coefficients and the noise distribution.

## Agent policies

For a cash amount `v > 0`, the CRRA policy uses

```text
u(v) = v^(1 - gamma) / (1 - gamma), with gamma < 1.
```

Each preset declares its complete gamma grid; the simulator does not infer risk parameters from output positions. The CLI validates finite, strictly increasing gamma values in `[-10, 1)`. At `gamma = 0`, utility is linear. Increasing gamma within the supported range makes utility more concave; negative gamma makes utility convex. The demo grid includes both `-0.015` and `0.9`.

At each offer, the agent accepts when

```text
u(offer) >= mean(u(prize) for every remaining prize).
```

Equality accepts. The remaining-prize lottery includes the reserved case and treats each unopened prize as equally likely. The comparison does not value future offers or optimize a continuation policy. In particular, a risk-neutral agent following this rule is not necessarily an agent that maximizes expected final winnings across the whole game.

The synthetic utility model uses monotone points derived from a normalized square-root curve and linear interpolation between adjacent cash points. Its JSON format records integer `cash_cents` and finite `utility` values. Cash points must strictly increase and utility values must not decrease. Rust and Python share this representation and interpolation semantics. The survey and verification tools use certainty equivalents; the inverse selects the leftmost cash amount when a utility plateau admits multiple answers.

## Randomness and paired comparisons

One complete trajectory supplies the case order and nine offers for every risk level and the synthetic utility agent. Accepting an offer changes only an agent's outcome; it does not alter the trajectory supplied to other agents. This common-random-number design makes differences between agents comparisons over the same games.

The current engine uses `SmallRng` from `rand` **0.10.0** with an explicit seed. A fixed seed is deterministic in the same implementation and environment. The project makes no promise of identical random streams or floating-point results across architectures, dependency updates, or future engine versions. Keep the configuration, lockfiles, toolchain versions, and run manifest with an experiment.

## Summary data

Summaries record the explicit gamma grid, game count, configuration, and distribution statistics. Monetary outputs use cents throughout.

| Summary | Definition |
| --- | --- |
| Mean | Arithmetic mean of all payouts |
| Median | Middle payout, or the mean of the two middle payouts for even `n` |
| Standard deviation | Population standard deviation, with divisor `n` |
| Quantiles | 1,001 points, including the minimum and maximum |
| Cash-out counts | Counts of accepted-offer rounds and final reserved-case payouts |
| Histogram | Upper-inclusive monetary buckets plus an overflow bucket |

For sorted payouts `x` and `n` games, quantile point `i` is

```text
q[i] = x[round((n - 1) * i / 1000)], for i = 0, ..., 1000.
```

The Rust rounding rule rounds half-integer indices upward. This nearest-index quantile rule differs from linear interpolation and from the median definition for an even sample.

The histogram's upper bounds, in dollars, are `500, 1,000, 10,000, 50,000, 100,000, 200,000, 300,000, 500,000, 750,000, 1,000,000`. Each boundary belongs to the lower bucket; an eleventh count captures values above the final bound. Preserve that overflow count when checking totals.

## Distribution analysis

The Python analysis treats the stored quantile points as equally weighted samples. For a target `t` in cents, it approximates:

```text
P(payout >= t)       = mean(q >= t)
integrated CDF at t  = mean(max(t - q, 0))
```

The integrated CDF is an expected shortfall below the target and has units of cents. It is the integral of the CDF up to the target, not a CDF-height calculation. Both quantities are approximations to the full empirical payout distribution because the output retains quantiles rather than every payout.

Comparing a finite list of targets does not prove first- or second-order stochastic dominance. Plots and tables describe the sampled agents and targets only. Optional plot smoothing is a display setting; it does not change the stored statistics or analysis calculations.

## Resource model and limitations

Exact quantiles require retaining payouts. The simulator estimates memory before allocating: the outcome arrays use four bytes per trial per agent, with summary storage included in the checked estimate. The default limit is 512 MiB. This guards an estimate rather than measuring process resident memory; runtime, plotting, and allocator overhead also matter.

The experiment uses a fixed prize board, a heuristic banker, and a static utility acceptance rule. It does not model wealth outside the game, changing preferences, strategic interaction with the banker, or an optimal stopping policy. Monte Carlo sample size, the selected gamma grid, and quantile compression limit how finely results can be interpreted.

Earlier generated results are superseded because the former implementation omitted the ninth offer, paid an incorrect case after declines, and calculated the integrated CDF incorrectly. The current documented pipeline is the basis for published figures.
