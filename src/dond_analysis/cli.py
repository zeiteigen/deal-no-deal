"""Command-line interface for experiments, figures and calibration."""

import argparse
import json
import os
import subprocess
import sys


def parser():
    root = argparse.ArgumentParser(description="Reproducible Deal or No Deal research workflows")
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("demo", "research"):
        command = commands.add_parser(name, help=f"Run the {name} preset and export all figures")
        command.add_argument("--output", help="Output directory (default: results/<preset>)")
        command.add_argument("--force", action="store_true")
        command.add_argument("--trials", type=int, help="Override games for a quick smoke test")
    plot = commands.add_parser("plot", help="Export every figure from versioned result JSON")
    plot.add_argument("input")
    plot.add_argument("--output", required=True)
    plot.add_argument("--show", action="store_true")
    plot.add_argument("--smoothing", type=int, default=1)
    analyze = commands.add_parser("analyze", help="Print approximate threshold metrics as JSON")
    analyze.add_argument("input")
    analyze.add_argument(
        "--targets", type=float, nargs="+", default=[39075, 190000, 280000, 450000]
    )
    survey = commands.add_parser("survey", help="Save certainty-equivalent survey points locally")
    survey.add_argument("--output", required=True)
    survey.add_argument("--layers", type=int, default=3)
    survey.add_argument("--seed", type=int, default=102)
    survey.add_argument("--force", action="store_true")
    verify = commands.add_parser(
        "verify", help="Interactively compare decisions with a utility model"
    )
    verify.add_argument("--model", required=True)
    verify.add_argument("--seed", type=int, default=102)
    commands.add_parser("baseline", help="Print original prize distribution statistics")
    return root


def execute(args):
    if args.command in ("demo", "research", "plot"):
        if args.command != "plot" or not args.show:
            os.environ.setdefault("MPLBACKEND", "Agg")
    if args.command in ("demo", "research"):
        from .workflow import run_preset

        return run_preset(args.command, args.output, args.force, args.trials)
    if args.command == "plot":
        from .data import load_results
        from .plots import render_all

        paths = render_all(load_results(args.input), args.output, args.show, args.smoothing)
        print(f"Saved {len(paths)} figures to {args.output}")
    elif args.command == "analyze":
        from .data import load_results
        from .metrics import integrated_cdf, threshold_probability

        document = load_results(args.input)
        rows = []
        for summary in document["summaries"]:
            for target in args.targets:
                rows.append(
                    {
                        "agent": summary["agent"],
                        "gamma": summary["gamma"],
                        "target_dollars": target,
                        "approx_probability_at_least": threshold_probability(
                            summary["quantiles_cents"], target * 100
                        ),
                        "approx_integrated_cdf_dollars": integrated_cdf(
                            summary["quantiles_cents"], target * 100
                        )
                        / 100,
                    }
                )
        print(json.dumps(rows, indent=2))
    elif args.command == "survey":
        from .calibration.survey import run_survey

        run_survey(args.output, args.layers, args.seed, args.force)
    elif args.command == "verify":
        from .calibration.verify import run_verification

        run_verification(args.model, args.seed, interactive=True)
    elif args.command == "baseline":
        import statistics

        from .data import PRIZES_CENTS

        prizes = [cents / 100 for cents in PRIZES_CENTS]
        print(
            json.dumps(
                {
                    "mean_dollars": statistics.mean(prizes),
                    "median_dollars": statistics.median(prizes),
                    "population_std_dev_dollars": statistics.pstdev(prizes),
                },
                indent=2,
            )
        )


def main():
    args = parser().parse_args()
    try:
        execute(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except EOFError, KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        return 130
    return 0
