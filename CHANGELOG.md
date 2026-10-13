# Changelog

## Unreleased

- Reorganize the project into a Rust simulation workspace and an installable Python analysis package.
- Add explicit demo, research, and large-run configurations, pinned toolchains, and dependency lockfiles.
- Evaluate CRRA and synthetic utility agents on complete shared trajectories with a fixed seed.
- Include all nine banker offers and pay the reserved case after rejecting the ninth offer.
- Store explicit risk grids, integer-cent payout summaries, 1,001 quantiles, and histograms with an overflow bucket.
- Add resource estimates and memory limits before simulation allocation.
- Add command-line orchestration, manifests, headless figures, threshold analysis, utility surveys, and model verification.
- Correct integrated CDF analysis to use expected shortfall below the target; remove unsupported stochastic-dominance claims.
- Add methodology, reproduction instructions, selected research figures, contributor guidance, citation metadata, and Ubuntu/Windows CI.
- Exclude generated results and personal survey artifacts from the public project. Earlier results are superseded by the corrected pipeline.
- Record the compiler and Cargo that built the simulator in run manifests, and reject output names ending in `.manifest.json`.
- Re-prompt for invalid survey answers (accepting `$` and thousands separators) and exit cleanly when a session is cancelled.
- Remove stale figures when a preset is rerun with `--force`, and count only the current run's files in `artifact_bytes`.
- Apply `--smoothing` only across the risk axis; density plots rely on the KDE bandwidth.
