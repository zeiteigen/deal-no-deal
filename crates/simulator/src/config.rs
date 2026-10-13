//! Resolved experiment configuration and pre-allocation bounds.
use crate::utility::UtilityModel;
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Preset {
    pub trials: u32,
    pub seed: u64,
    pub gammas: Vec<f64>,
    #[serde(default = "default_limit")]
    pub memory_limit_mib: u64,
}
fn default_limit() -> u64 {
    512
}

#[derive(Clone, Debug, Serialize)]
pub struct Config {
    pub mode: String,
    pub trials: u32,
    pub seed: u64,
    pub gammas: Vec<f64>,
    pub utility: Option<UtilityModel>,
    pub memory_limit_mib: u64,
}

impl Config {
    pub fn validate(&self) -> Result<u64, String> {
        if self.trials == 0 {
            return Err("Trials must be greater than zero".into());
        }
        let agents = match self.mode.as_str() {
            "sweep" => {
                if self.gammas.is_empty()
                    || self
                        .gammas
                        .iter()
                        .any(|g| !g.is_finite() || *g >= 1.0 || *g < -10.0)
                    || self.gammas.windows(2).any(|w| w[0] >= w[1])
                {
                    return Err(
                        "Gammas must strictly increase, be finite, and lie in [-10, 1)".into(),
                    );
                }
                self.gammas.len()
            }
            "single" => {
                let model = self
                    .utility
                    .as_ref()
                    .ok_or("Single mode requires --model")?;
                model.validate()?;
                if model.points.first().unwrap().cash_cents > 0
                    || model.points.last().unwrap().cash_cents < 100_000_000
                {
                    return Err(
                        "Simulation utility domain must cover 0 through 100000000 cents".into(),
                    );
                }
                1
            }
            _ => return Err("Mode must be sweep or single".into()),
        };
        let bytes = u64::from(self.trials)
            .checked_mul(agents as u64)
            .and_then(|n| n.checked_mul(4))
            .ok_or("Outcome storage size overflows")?;
        let limit = self
            .memory_limit_mib
            .checked_mul(1024 * 1024)
            .ok_or("Memory limit overflows")?;
        // Quantile arrays, serialization buffers and per-agent bookkeeping get a conservative allowance.
        let budget = bytes
            .checked_add(
                (agents as u64)
                    .checked_mul(128 * 1024)
                    .ok_or("Summary storage size overflows")?,
            )
            .ok_or("Storage size overflows")?;
        if budget > limit {
            return Err(format!(
                "Estimated outcomes + summary buffers require {} MiB, exceeding --memory-limit-mib {}",
                budget.div_ceil(1024 * 1024),
                self.memory_limit_mib
            ));
        }
        Ok(bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        Config {
            mode: "sweep".into(),
            trials: 10,
            seed: 102,
            gammas: vec![0.0, 0.5],
            utility: None,
            memory_limit_mib: 512,
        }
    }
    #[test]
    fn rejects_empty_invalid_and_large_experiments() {
        let mut c = config();
        assert_eq!(c.validate().unwrap(), 80);
        c.trials = 0;
        assert!(c.validate().is_err());
        c.trials = 10;
        c.gammas = vec![0.5, 0.0];
        assert!(c.validate().is_err());
        c.gammas = vec![1.0];
        assert!(c.validate().is_err());
        c.gammas = vec![0.0];
        c.trials = 1_000_000;
        c.memory_limit_mib = 1;
        assert!(c.validate().is_err());
    }
}
