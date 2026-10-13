# Reproducing experiments

Run all commands from the repository root. Install Rust through rustup and install uv. The repository pins Rust 1.98.0 in `rust-toolchain.toml`, Python 3.14.7 in `.python-version`, and dependencies in `Cargo.lock` and `uv.lock`.

```bash
uv sync --locked
cargo build --release --locked --bin dond-sim
```

The `--locked` commands fail if the dependency files need an update. For a reproducible run, record the source revision and keep the configuration and generated manifests together with the outputs.

## Presets

| Preset | Trials | CRRA levels | Seed | Use |
| --- | ---: | ---: | ---: | --- |
| `examples/demo.json` | 1,000 | 41 | 102 | End-to-end smoke run and exploration |
| `examples/research.json` | 100,000 | 201 | 102 | Published research figures |
| `examples/large.json` | 1,000,000 | 1,000 | 102 | Explicit high-resource experiment |

Each preset contains an explicit gamma grid. Python orchestration separately runs the checked-in synthetic utility model. The large preset raises the memory limit to 8,192 MiB. Its payout arrays alone occupy approximately 3.73 GiB for 1,000 CRRA agents; the model, summaries, and process overhead need additional memory. Start with the demo before choosing a larger configuration. Measured runtime and output sizes belong in [results](results.md).

## Python orchestration

```bash
uv run dond demo
uv run dond research
```

The default directories are `results/demo/` and `results/research/`. Use `--output` to choose another run directory:

```bash
uv run dond demo --output results/my-demo
uv run dond research --output results/my-research
```

Each command runs the CRRA sweep and the synthetic single agent, then creates five figures in both PNG and SVG. The run directory contains `sweep.json`, `single.json`, and their `*.manifest.json` files. Figure basenames are `win_statistics`, `probability_density`, `cash_out`, `threshold_probability`, and `integrated_cdf`.

Each simulator manifest records runtime, outcome storage, and Rust platform and tool versions. Orchestrated runs enrich these files with Python and CPU information, source revision, dirty state, and a source-content hash. `workflow.manifest.json` records the combined runtime, generated artifact bytes, preset, and source metadata. Inspect them when comparing or sharing results. Use `--force` only when you intend to replace existing outputs:

```bash
uv run dond demo --output results/my-demo --force
```

Generated output belongs in the ignored `results/` directory. The selected images under `docs/assets/` are publication artifacts copied from a documented research run.

`examples/sample-output.json` is the synthetic agent's generated demo summary. It lets you exercise loading, analysis, and plotting without running Rust:

```bash
uv run dond plot examples/sample-output.json --output results/sample-figures
```

## Direct Rust commands

Run a sweep using an explicit configuration:

```bash
cargo run --release --locked --bin dond-sim -- sweep --config examples/demo.json --output results/custom/sweep.json
```

Supported overrides include `--trials`, `--seed`, `--output`, and `--memory-limit-mib`. They make the effective experiment differ from the preset, so retain the manifest when reporting the run.

```bash
cargo run --release --locked --bin dond-sim -- sweep --config examples/demo.json --trials 2000 --seed 103 --output results/custom/sweep.json
```

Run the piecewise-linear agent with an explicit utility model:

```bash
cargo run --release --locked --bin dond-sim -- single --config examples/demo.json --model examples/synthetic-utility.json --output results/custom/single.json
```

The default memory limit is 512 MiB. A run rejected by the estimate needs a smaller trial count or agent grid, or an explicit higher `--memory-limit-mib` backed by available memory. `--force` permits output replacement; it is not a substitute for budgeting a large run.

## Plot and analyze saved summaries

```bash
uv run dond plot results/research/sweep.json --output results/research/figures
uv run dond plot results/research/sweep.json --output results/research/figures --show --smoothing 3
uv run dond analyze results/research/sweep.json --targets 39075 190000 280000 450000
```

Plotting is headless by default. `--show` requests interactive display and needs a suitable local plotting backend. `--smoothing` averages neighbouring risk levels in figures with a γ axis; it affects presentation only and leaves density plots unchanged. The target arguments are dollars, although summaries and derived shortfall values use cents. Analysis uses compressed quantiles, so threshold probabilities and integrated CDF values approximate the empirical distribution. See [methodology](methodology.md) for their definitions and limits.

## Survey and verification

```bash
uv run dond survey --output personal/model.json --layers 3 --seed 102
uv run dond verify --model examples/synthetic-utility.json --seed 102
```

Survey responses create a monotone piecewise-linear utility model. A seed controls generated survey choices; responses remain personal inputs and are not made reproducible by a seed alone. Use `personal/` for survey output and keep it outside version control. For a reproducible public single-agent experiment, use the checked-in synthetic model or another intentionally published model.

## Development verification

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run dond demo --output results/check
```

Ubuntu CI runs the formatting, lint, test, and full demo checks and uploads only the demo's generated outputs. Windows CI runs Rust and Python smoke checks with a small sweep. Local results can be deterministic within one environment without being byte-identical across operating systems or architectures.
