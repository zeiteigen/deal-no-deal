//! Thin command-line entrypoint. Experiment behavior lives in the library.
use dond_simulator::{
    config::{Config, Preset},
    output, simulation,
    utility::UtilityModel,
};
use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    time::{Instant, SystemTime, UNIX_EPOCH},
};

const HELP: &str = "dond-sim <sweep|single|utility> [options]\n\n  --config FILE         Experiment preset JSON (defaults to demo)\n  --trials N            Positive game count\n  --seed N              Seed (default 102)\n  --model FILE          Shared utility JSON, required for single/utility\n  --output FILE         Output JSON, required for simulations\n  --memory-limit-mib N  Outcomes + summary storage budget (default 512)\n  --cash-cents N        Utility evaluation input, for utility mode\n  --force               Replace existing outputs\n  --help                Show this help";

fn parse() -> Result<(String, BTreeMap<String, String>, bool), String> {
    let mut args = std::env::args().skip(1);
    let mode = args.next().unwrap_or_else(|| "--help".into());
    if mode == "--help" || mode == "-h" {
        println!("{HELP}");
        std::process::exit(0);
    }
    if !["sweep", "single", "utility"].contains(&mode.as_str()) {
        return Err(format!("Unknown mode {mode}\n{HELP}"));
    }
    let mut options = BTreeMap::new();
    let mut force = false;
    while let Some(arg) = args.next() {
        if arg == "--help" {
            println!("{HELP}");
            std::process::exit(0);
        }
        if arg == "--force" {
            force = true;
            continue;
        }
        if ![
            "--config",
            "--trials",
            "--seed",
            "--model",
            "--output",
            "--memory-limit-mib",
            "--cash-cents",
        ]
        .contains(&arg.as_str())
        {
            return Err(format!("Unknown option {arg}"));
        }
        let value = args
            .next()
            .ok_or_else(|| format!("{arg} requires a value"))?;
        if options.insert(arg.clone(), value).is_some() {
            return Err(format!("Repeated option {arg}"));
        }
    }
    Ok((mode, options, force))
}

fn read_model(options: &BTreeMap<String, String>) -> Result<UtilityModel, String> {
    let path = options.get("--model").ok_or("--model is required")?;
    let model: UtilityModel = serde_json::from_str(
        &fs::read_to_string(path).map_err(|e| format!("Cannot read model {path}: {e}"))?,
    )
    .map_err(|e| format!("Invalid utility JSON: {e}"))?;
    model.validate()?;
    Ok(model)
}
fn execute() -> Result<(), String> {
    let (mode, options, force) = parse()?;
    if mode == "utility" {
        let cash: u32 = options
            .get("--cash-cents")
            .ok_or("--cash-cents is required")?
            .parse()
            .map_err(|_| "--cash-cents requires an integer")?;
        println!("{}", read_model(&options)?.evaluate(cash)?);
        return Ok(());
    }
    let preset_source = match options.get("--config") {
        Some(path) => {
            fs::read_to_string(path).map_err(|e| format!("Cannot read config {path}: {e}"))?
        }
        None => include_str!("../../../examples/demo.json").into(),
    };
    let mut preset: Preset =
        serde_json::from_str(&preset_source).map_err(|e| format!("Invalid preset: {e}"))?;
    if let Some(value) = options.get("--trials") {
        preset.trials = value
            .parse()
            .map_err(|_| "--trials requires a positive integer")?;
    }
    if let Some(value) = options.get("--seed") {
        preset.seed = value
            .parse()
            .map_err(|_| "--seed requires an unsigned integer")?;
    }
    if let Some(value) = options.get("--memory-limit-mib") {
        preset.memory_limit_mib = value
            .parse()
            .map_err(|_| "--memory-limit-mib requires an unsigned integer")?;
    }
    if mode == "sweep" && options.contains_key("--model") {
        return Err("--model applies only to single or utility mode".into());
    }
    if options.contains_key("--cash-cents") {
        return Err("--cash-cents applies only to utility mode".into());
    }
    let config = Config {
        mode: mode.clone(),
        trials: preset.trials,
        seed: preset.seed,
        gammas: if mode == "sweep" {
            preset.gammas
        } else {
            vec![]
        },
        utility: if mode == "single" {
            Some(read_model(&options)?)
        } else {
            None
        },
        memory_limit_mib: preset.memory_limit_mib,
    };
    let bytes = config.validate()?;
    let path = PathBuf::from(options.get("--output").ok_or("--output FILE is required")?);
    if path.file_name().is_none() || path.is_dir() {
        return Err("--output must name a JSON file".into());
    }
    if path.to_string_lossy().ends_with(".manifest.json") {
        return Err("--output cannot end in .manifest.json".into());
    }
    let manifest_path = output::manifest_path(&path);
    for destination in [&path, &manifest_path] {
        if destination.exists() && !force {
            return Err(format!(
                "{} already exists; choose another output or pass --force",
                destination.display()
            ));
        }
    }
    // Fail on inaccessible destinations before performing an expensive simulation.
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    fs::create_dir_all(parent).map_err(|e| format!("Cannot create output directory: {e}"))?;
    eprintln!(
        "Outcome storage: {:.2} MiB; seed {}; mode {}",
        bytes as f64 / 1_048_576.0,
        config.seed,
        mode
    );
    let started = Instant::now();
    let envelope = simulation::run(config)?;
    let elapsed = started.elapsed().as_secs_f64();
    output::write_json(&path, &envelope, force)?;
    let manifest = serde_json::json!({
        "schema_version":1,"model_version":"1.0.0","result_file":path.file_name().unwrap().to_string_lossy(),
        "elapsed_seconds":elapsed,"outcome_storage_bytes":bytes,
        "timestamp_unix":SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e|e.to_string())?.as_secs(),
        "platform":std::env::consts::OS,"architecture":std::env::consts::ARCH,"rustc":env!("DOND_BUILD_RUSTC"),"cargo":env!("DOND_BUILD_CARGO"),
    });
    output::write_json(&manifest_path, &manifest, force)?;
    eprintln!("Wrote {} in {:.3} seconds", path.display(), elapsed);
    Ok(())
}

fn main() {
    if let Err(error) = execute() {
        eprintln!("Error: {error}");
        std::process::exit(1);
    }
}
