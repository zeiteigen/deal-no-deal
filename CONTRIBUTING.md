# Contributing

Use the pinned Rust and Python toolchains and the committed lockfiles. From the repository root:

```bash
uv sync --locked
cargo build --locked --bin dond-sim
```

Keep modules focused on one or two responsibilities. Rust owns game generation, policies, and summaries; Python owns orchestration, analysis, figures, and calibration. Keep cash in integer cents at the interchange boundary, and convert to dollars explicitly for display or CLI inputs.

Before submitting a change, run:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run dond demo --output results/contribution-check
```

An existing output directory requires a new path or an intentional `--force`. CI runs the complete checks on Ubuntu, a smaller Rust and Python smoke run on Windows, and uploads Ubuntu demo outputs for inspection.

For behavioral changes, add a focused regression check for the affected rule. Useful checks include nine-offer coverage, reserved-case payouts, equality acceptance, common trajectories, quantile endpoints, histogram totals, and agreement between Rust and Python utility evaluation. Avoid tests that simply restate implementation details.

Changes to game rules, banker coefficients, RNG behavior, utility semantics, or summary schemas can invalidate published comparisons. Explain the change, update the methodology and changelog, and regenerate the relevant figures from a recorded configuration. Preserve manifests when discussing results. Treat Monte Carlo findings as conditional on the model and sample; do not infer stochastic dominance from a few threshold comparisons.

Keep generated data in `results/` and personal survey artifacts in `personal/`. Commit only deliberately selected public figures and synthetic examples. Do not add personal responses, credentials, caches, or legacy experiment output. Dependency changes should update the corresponding lockfile deliberately and include the reason for the update.

Pull requests should describe the concrete behavior changed and the checks run. Include before/after evidence where it helps a reviewer assess a simulation or analysis change.
