//! Complete game trajectories, independent of agent decisions.
use crate::rules::{BANKER_COEFFICIENTS, CASES, OPENED};
use rand::{RngExt, rngs::SmallRng, seq::SliceRandom};

#[derive(Debug)]
pub struct Round {
    pub remaining_cases: Vec<u32>,
    pub offer_cents: u32,
}

#[derive(Debug)]
pub struct Trajectory {
    pub rounds: [Round; 9],
    pub reserved_case_cents: u32,
}

pub fn generate(rng: &mut SmallRng) -> Trajectory {
    let mut order = CASES;
    order.shuffle(rng);
    let reserved_case_cents = order[25];
    let mut opened = 0;
    let rounds = std::array::from_fn(|index| {
        opened += OPENED[index];
        let remaining_cases = order[opened..].to_vec();
        let mean = remaining_cases.iter().map(|&v| u64::from(v)).sum::<u64>() as f64
            / remaining_cases.len() as f64;
        let offer_cents =
            (mean * BANKER_COEFFICIENTS[index] * rng.random_range(0.95..=1.05)) as u32;
        Round {
            remaining_cases,
            offer_cents,
        }
    });
    Trajectory {
        rounds,
        reserved_case_cents,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;

    #[test]
    fn nine_rounds_leave_reserved_case_in_play() {
        let game = generate(&mut SmallRng::seed_from_u64(102));
        assert_eq!(
            game.rounds.each_ref().map(|r| r.remaining_cases.len()),
            [20, 15, 11, 8, 6, 5, 4, 3, 2]
        );
        for round in &game.rounds {
            assert!(round.remaining_cases.contains(&game.reserved_case_cents));
            let mean = round
                .remaining_cases
                .iter()
                .map(|&v| f64::from(v))
                .sum::<f64>()
                / round.remaining_cases.len() as f64;
            assert!(round.offer_cents > 0);
            assert!(f64::from(round.offer_cents) <= mean * 1.01 * 1.05);
        }
    }
}
