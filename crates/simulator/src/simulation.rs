//! Seeded experiment execution with shared trajectories across agents.
use crate::{config::Config, game, output::Envelope, policy, statistics::Accumulator};
use rand::{SeedableRng, rngs::SmallRng};

pub fn run(config: Config) -> Result<Envelope, String> {
    config.validate()?;
    let mut rng = SmallRng::seed_from_u64(config.seed);
    let count = if config.mode == "sweep" {
        config.gammas.len()
    } else {
        1
    };
    let mut accumulators = (0..count)
        .map(|_| Accumulator::new(config.trials as usize))
        .collect::<Result<Vec<_>, _>>()?;
    for trial in 0..config.trials {
        let game = game::generate(&mut rng);
        if config.mode == "sweep" {
            let low = config.gammas[0];
            let high = config.gammas[count - 1];
            let thresholds = game
                .rounds
                .each_ref()
                .map(|r| policy::threshold(r, low, high));
            for (accumulator, &gamma) in accumulators.iter_mut().zip(&config.gammas) {
                accumulator.push(policy::crra_outcome(&game, gamma, &thresholds));
            }
        } else {
            accumulators[0].push(policy::utility_outcome(
                &game,
                config.utility.as_ref().unwrap(),
            )?);
        }
        if (trial + 1).is_multiple_of(10_000) {
            eprintln!("Simulated {} / {} games", trial + 1, config.trials);
        }
    }
    let summaries = accumulators
        .into_iter()
        .enumerate()
        .map(|(i, a)| {
            if config.mode == "sweep" {
                a.summarize(Some(config.gammas[i]), "crra".into())
            } else {
                a.summarize(None, config.utility.as_ref().unwrap().name.clone())
            }
        })
        .collect();
    Ok(Envelope {
        schema_version: 1,
        model_version: "1.0.0".into(),
        currency_unit: "cents".into(),
        rng: "rand::rngs::SmallRng (rand 0.10.0)".into(),
        config,
        summaries,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn repeat_seed_is_identical_and_counts_match() {
        let c = Config {
            mode: "sweep".into(),
            trials: 20,
            seed: 102,
            gammas: vec![-0.015, 0.5, 0.9],
            utility: None,
            memory_limit_mib: 512,
        };
        let a = run(c.clone()).unwrap();
        let b = run(c).unwrap();
        assert_eq!(
            serde_json::to_vec(&a).unwrap(),
            serde_json::to_vec(&b).unwrap()
        );
        for summary in a.summaries {
            assert_eq!(summary.sample_size, 20);
            assert_eq!(
                summary.cash_out_rounds.iter().sum::<u32>() + summary.kept_case,
                20
            );
        }
    }
}
