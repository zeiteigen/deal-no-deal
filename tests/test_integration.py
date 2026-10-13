"""Verify the Rust/Python contract and documented workflows."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dond_analysis.data import load_results
from dond_analysis.utility import load_utility

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def simulator():
    subprocess.run(["cargo", "build", "--locked", "--bin", "dond-sim"], cwd=ROOT, check=True)
    name = "dond-sim.exe" if sys.platform == "win32" else "dond-sim"
    return ROOT / "target" / "debug" / name


def run(simulator, *arguments):
    return subprocess.run(
        [str(simulator), *map(str, arguments)], capture_output=True, text=True, check=False
    )


def test_both_modes_and_same_seed(simulator, tmp_path):
    outputs = []
    for mode in ("sweep", "single"):
        output = tmp_path / f"{mode}.json"
        args = [mode, "--trials", "16", "--output", output]
        if mode == "single":
            args.extend(["--model", ROOT / "examples" / "synthetic-utility.json"])
        result = run(simulator, *args)
        assert result.returncode == 0, result.stderr
        document = load_results(output)
        assert all(s["sample_size"] == 16 for s in document["summaries"])
        manifest = json.loads(output.with_suffix(".manifest.json").read_text())
        assert manifest["outcome_storage_bytes"] == 16 * 4 * len(document["summaries"])
        assert manifest["rustc"].startswith("rustc ")
        original = output.read_bytes()
        assert run(simulator, *args).returncode != 0
        assert output.read_bytes() == original
        assert run(simulator, *args, "--force").returncode == 0
        assert output.read_bytes() == original
        outputs.append(document)
    assert outputs[1]["summaries"][0]["gamma"] is None


def test_linear_agent_matches_risk_neutral_trajectories(simulator, tmp_path):
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps({"trials": 100, "seed": 102, "gammas": [0.0]}))
    model = tmp_path / "model.json"
    model.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "name": "linear",
                "points": [
                    {"cash_cents": 0, "utility": 0},
                    {"cash_cents": 100_000_000, "utility": 100_000_000},
                ],
            }
        )
    )
    summaries = []
    for mode in ("sweep", "single"):
        output = tmp_path / f"{mode}.json"
        args = [mode, "--config", preset, "--output", output]
        if mode == "single":
            args.extend(["--model", model])
        result = run(simulator, *args)
        assert result.returncode == 0, result.stderr
        summary = load_results(output)["summaries"][0]
        summaries.append({k: v for k, v in summary.items() if k not in ("agent", "gamma")})
    assert summaries[0] == summaries[1]


@pytest.mark.parametrize("cash", [0, 1, 390625, 1234567, 25000000, 100000000])
def test_cross_language_utility(simulator, cash):
    model = ROOT / "examples" / "synthetic-utility.json"
    result = run(simulator, "utility", "--model", model, "--cash-cents", cash)
    assert result.returncode == 0, result.stderr
    assert float(result.stdout) == pytest.approx(load_utility(model).evaluate(cash), abs=1e-12)


@pytest.mark.parametrize(
    "options,message",
    [
        (["--trials", "0"], "Trials"),
        (["--memory-limit-mib", "0"], "exceeding"),
        (["--config", "missing-config.json"], "Cannot read config"),
        (["--trials", "abc"], "integer"),
        (["--unknown", "1"], "Unknown option"),
    ],
)
def test_invalid_inputs_fail_without_output(simulator, tmp_path, options, message):
    output = tmp_path / "result.json"
    result = run(simulator, "sweep", "--output", output, *options)
    assert result.returncode != 0
    assert message in result.stderr
    assert not output.exists()


def test_existing_manifest_and_bad_parent(simulator, tmp_path):
    output = tmp_path / "result.json"
    output.with_suffix(".manifest.json").write_text("existing")
    result = run(simulator, "sweep", "--output", output, "--trials", "1")
    assert result.returncode != 0 and "already exists" in result.stderr
    assert not output.exists()
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    result = run(simulator, "sweep", "--output", blocker / "result.json", "--trials", "1")
    assert result.returncode != 0 and "output directory" in result.stderr


def test_output_cannot_be_a_manifest_name(simulator, tmp_path):
    output = tmp_path / "result.manifest.json"
    result = run(simulator, "sweep", "--output", output, "--trials", "1")
    assert result.returncode != 0 and ".manifest.json" in result.stderr
    assert not output.exists()


def demo(tmp_path, output, *extra):
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from dond_analysis.cli import main; raise SystemExit(main())",
            "demo",
            "--trials",
            "3",
            "--output",
            str(output),
            *extra,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_demo_from_another_directory(tmp_path):
    output = tmp_path / "demo"
    result = demo(tmp_path, output)
    assert result.returncode == 0, result.stderr
    assert load_results(output / "sweep.json")["config"]["trials"] == 3
    assert load_results(output / "single.json")["config"]["trials"] == 3
    assert len(list((output / "figures").rglob("*.png"))) == 10
    assert len(list((output / "figures").rglob("*.svg"))) == 10
    manifest = json.loads((output / "workflow.manifest.json").read_text())
    assert len(manifest["source_sha256"]) == 64
    assert manifest["elapsed_seconds"] > 0
    produced = [output / name for name in ("sweep.json", "single.json")]
    produced += [p.with_suffix(".manifest.json") for p in produced]
    produced += [p for p in (output / "figures").rglob("*") if p.is_file()]
    assert manifest["artifact_bytes"] == sum(p.stat().st_size for p in produced)


def test_forced_demo_removes_stale_figures(tmp_path):
    output = tmp_path / "demo"
    stale = output / "figures" / "sweep" / "renamed_figure.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"old")
    result = demo(tmp_path, output, "--force")
    assert result.returncode == 0, result.stderr
    assert not stale.exists()
    assert len(list((output / "figures").rglob("*.png"))) == 10
