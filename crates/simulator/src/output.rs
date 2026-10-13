//! Versioned result serialization and protected atomic file replacement.
use crate::{config::Config, statistics::Summary};
use serde::Serialize;
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
};

#[derive(Debug, Serialize)]
pub struct Envelope {
    pub schema_version: u32,
    pub model_version: String,
    pub currency_unit: String,
    pub rng: String,
    pub config: Config,
    pub summaries: Vec<Summary>,
}

pub fn manifest_path(output: &Path) -> PathBuf {
    output.with_extension("manifest.json")
}

pub fn write_json(path: &Path, value: &impl Serialize, force: bool) -> Result<(), String> {
    if path.exists() && !force {
        return Err(format!(
            "{} already exists; choose another output or pass --force",
            path.display()
        ));
    }
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    fs::create_dir_all(parent).map_err(|e| format!("Cannot create {}: {e}", parent.display()))?;
    let temporary = parent.join(format!(
        ".{}.{}.tmp",
        path.file_name().unwrap().to_string_lossy(),
        std::process::id()
    ));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)
            .map_err(|e| e.to_string())?;
        serde_json::to_writer_pretty(&mut file, value).map_err(|e| e.to_string())?;
        file.write_all(b"\n").map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        if force {
            // std::fs::rename replaces existing files on supported Unix and Windows filesystems.
            fs::rename(&temporary, path).map_err(|e| e.to_string())?;
        } else {
            // A hard link atomically refuses a concurrently created destination.
            fs::hard_link(&temporary, path).map_err(|e| e.to_string())?;
            fs::remove_file(&temporary).map_err(|e| e.to_string())?;
        }
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.map_err(|e: String| format!("Unable to write {}: {e}", path.display()))
}
