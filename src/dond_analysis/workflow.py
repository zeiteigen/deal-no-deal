"""Run repository presets and collect reproducibility metadata."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .data import load_results
from .plots import render_all


def repository_root():
    root = Path(__file__).resolve().parents[2]
    if not (root / "Cargo.toml").exists():
        raise ValueError("Run this workflow from an editable checkout installed with uv sync")
    return root


def source_metadata(root):
    digest = hashlib.sha256()
    paths = [root / name for name in ("Cargo.toml", "Cargo.lock", "pyproject.toml", "uv.lock")]
    for folder, pattern in (("crates", "*.rs"), ("src", "*.py"), ("examples", "*.json")):
        paths.extend((root / folder).rglob(pattern))
    for path in sorted(paths):
        if path.is_file() and path.name != "sample-output.json":
            digest.update(str(path.relative_to(root)).encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    revision, dirty = None, None
    if shutil.which("git"):
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=False
        )
        if commit.returncode == 0:
            revision = commit.stdout.strip()
        if status.returncode == 0:
            dirty = bool(status.stdout.strip())
    return {"source_sha256": digest.hexdigest(), "source_revision": revision, "source_dirty": dirty}


def run_preset(name, output=None, force=False, trials=None):
    root = repository_root()
    directory = Path(output) if output else root / "results" / name
    if directory.exists() and any(directory.iterdir()) and not force:
        raise ValueError(f"{directory} is not empty; select another output or pass --force")
    if not shutil.which("cargo"):
        raise ValueError(
            "Cargo is missing; install the Rust toolchain described in docs/reproduction.md"
        )
    directory.mkdir(parents=True, exist_ok=True)
    preset = root / "examples" / f"{name}.json"
    if not preset.is_file():
        raise ValueError(f"Unknown preset: {name}")
    started = time.perf_counter()
    metadata = source_metadata(root)
    artifacts = []
    for mode in ("sweep", "single"):
        result = directory / f"{mode}.json"
        command = [
            "cargo",
            "run",
            "--release",
            "--locked",
            "--manifest-path",
            str(root / "Cargo.toml"),
            "--bin",
            "dond-sim",
            "--",
            mode,
            "--config",
            str(preset),
            "--output",
            str(result),
        ]
        if mode == "single":
            command.extend(["--model", str(root / "examples" / "synthetic-utility.json")])
        if trials is not None:
            command.extend(["--trials", str(trials)])
        if force:
            command.append("--force")
        subprocess.run(command, cwd=root, check=True)
        manifest_path = result.with_suffix(".manifest.json")
        manifest = json.loads(manifest_path.read_text())
        manifest.update(metadata)
        manifest.update(
            python=sys.version.split()[0],
            machine=platform.machine(),
            processor=platform.processor(),
            logical_cpus=os.cpu_count(),
            preset=name,
        )
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        figures = directory / "figures" / mode
        if force and figures.is_dir():
            # Remove figures from earlier runs so the directory matches this run only.
            for stale in figures.iterdir():
                if stale.is_file() and stale.suffix in (".png", ".svg"):
                    stale.unlink()
        artifacts += [result, manifest_path, *render_all(load_results(result), figures)]
    elapsed = time.perf_counter() - started
    artifact_bytes = sum(path.stat().st_size for path in artifacts)
    (directory / "workflow.manifest.json").write_text(
        json.dumps(
            {
                **metadata,
                "preset": name,
                "elapsed_seconds": elapsed,
                "artifact_bytes": artifact_bytes,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"Generated {directory} in {elapsed:.2f}s ({artifact_bytes:,} artifact bytes)")
    return directory
