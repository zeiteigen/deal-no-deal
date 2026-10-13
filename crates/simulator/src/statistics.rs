//! Exact summary statistics and compressed distribution representation.
use crate::{policy::Outcome, rules::HISTOGRAM_BOUNDS};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct Histogram {
    pub upper_bounds_cents: [u32; 10],
    pub counts: [u32; 11],
}

#[derive(Debug, Serialize)]
pub struct Summary {
    pub gamma: Option<f64>,
    pub agent: String,
    pub sample_size: u32,
    pub mean_cents: f64,
    pub median_cents: f64,
    pub std_dev_cents: f64,
    pub quantile_probabilities: Vec<f64>,
    pub quantiles_cents: Vec<u32>,
    pub histogram: Histogram,
    pub cash_out_rounds: [u32; 9],
    pub kept_case: u32,
}

pub struct Accumulator {
    winnings: Vec<u32>,
    rounds: [u32; 9],
    kept: u32,
}

impl Accumulator {
    pub fn new(trials: usize) -> Result<Self, String> {
        let mut winnings = Vec::new();
        winnings
            .try_reserve_exact(trials)
            .map_err(|e| format!("Unable to allocate outcome storage: {e}"))?;
        Ok(Self {
            winnings,
            rounds: [0; 9],
            kept: 0,
        })
    }
    pub fn push(&mut self, outcome: Outcome) {
        self.winnings.push(outcome.cents);
        match outcome.cash_out_round {
            Some(r) => self.rounds[r - 1] += 1,
            None => self.kept += 1,
        }
    }
    pub fn summarize(mut self, gamma: Option<f64>, agent: String) -> Summary {
        self.winnings.sort_unstable();
        let len = self.winnings.len();
        let mean = self.winnings.iter().map(|&v| u64::from(v)).sum::<u64>() as f64 / len as f64;
        let median = if len.is_multiple_of(2) {
            (f64::from(self.winnings[len / 2 - 1]) + f64::from(self.winnings[len / 2])) / 2.0
        } else {
            f64::from(self.winnings[len / 2])
        };
        let std_dev = (self
            .winnings
            .iter()
            .map(|&v| (f64::from(v) - mean).powi(2))
            .sum::<f64>()
            / len as f64)
            .sqrt();
        let quantile_probabilities: Vec<f64> = (0..=1000).map(|i| f64::from(i) / 1000.0).collect();
        let quantiles_cents = quantile_probabilities
            .iter()
            .map(|p| self.winnings[(p * (len - 1) as f64).round() as usize])
            .collect();
        let mut counts = [0; 11];
        for &win in &self.winnings {
            counts[HISTOGRAM_BOUNDS.partition_point(|&edge| edge < win)] += 1;
        }
        Summary {
            gamma,
            agent,
            sample_size: len as u32,
            mean_cents: mean,
            median_cents: median,
            std_dev_cents: std_dev,
            quantile_probabilities,
            quantiles_cents,
            histogram: Histogram {
                upper_bounds_cents: HISTOGRAM_BOUNDS,
                counts,
            },
            cash_out_rounds: self.rounds,
            kept_case: self.kept,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn fractional_center_population_variance_and_count_invariants() {
        let mut a = Accumulator::new(2).unwrap();
        a.push(Outcome {
            cents: 1,
            cash_out_round: Some(9),
        });
        a.push(Outcome {
            cents: 2,
            cash_out_round: None,
        });
        let s = a.summarize(Some(0.0), "crra".into());
        assert_eq!(s.mean_cents, 1.5);
        assert_eq!(s.median_cents, 1.5);
        assert_eq!(s.std_dev_cents, 0.5);
        assert_eq!(s.quantiles_cents.len(), 1001);
        assert_eq!(s.quantiles_cents[0], 1);
        assert_eq!(s.quantiles_cents[1000], 2);
        assert!(s.quantiles_cents.windows(2).all(|w| w[0] <= w[1]));
        assert_eq!(s.cash_out_rounds.iter().sum::<u32>() + s.kept_case, 2);
        assert_eq!(s.histogram.counts.iter().sum::<u32>(), 2);
    }
    #[test]
    fn histogram_bounds_include_equality_and_overflow() {
        let mut a = Accumulator::new(2).unwrap();
        for cents in [50_000, 100_000_001] {
            a.push(Outcome {
                cents,
                cash_out_round: None,
            });
        }
        let s = a.summarize(None, "test".into());
        assert_eq!(s.histogram.counts[0], 1);
        assert_eq!(s.histogram.counts[10], 1);
    }
}
