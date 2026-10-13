//! Acceptance policies; equality accepts the guaranteed offer.
use crate::{
    game::{Round, Trajectory},
    utility::{UtilityModel, crra},
};

pub const RISK_TOLERANCE: f64 = 1e-8;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Outcome {
    pub cents: u32,
    pub cash_out_round: Option<usize>,
}

#[derive(Clone, Copy, Debug)]
pub enum Threshold {
    AllAccept,
    AllDecline,
    Crossing(f64),
}

pub fn accepts(round: &Round, gamma: f64) -> bool {
    crra(gamma, round.offer_cents)
        >= round
            .remaining_cases
            .iter()
            .map(|&v| crra(gamma, v))
            .sum::<f64>()
            / round.remaining_cases.len() as f64
}

pub fn threshold(round: &Round, low: f64, high: f64) -> Threshold {
    if accepts(round, low) {
        return Threshold::AllAccept;
    }
    if !accepts(round, high) {
        return Threshold::AllDecline;
    }
    let (mut left, mut right) = (low, high);
    for _ in 0..100 {
        if right - left <= RISK_TOLERANCE {
            break;
        }
        let mid = (left + right) / 2.0;
        if accepts(round, mid) {
            right = mid;
        } else {
            left = mid;
        }
    }
    Threshold::Crossing((left + right) / 2.0)
}

pub fn crra_outcome(game: &Trajectory, gamma: f64, thresholds: &[Threshold; 9]) -> Outcome {
    for (index, (round, threshold)) in game.rounds.iter().zip(thresholds).enumerate() {
        let take = match *threshold {
            Threshold::AllAccept => true,
            Threshold::AllDecline => false,
            Threshold::Crossing(crossing) if (gamma - crossing).abs() <= RISK_TOLERANCE => {
                accepts(round, gamma)
            }
            Threshold::Crossing(crossing) => gamma > crossing,
        };
        if take {
            return Outcome {
                cents: round.offer_cents,
                cash_out_round: Some(index + 1),
            };
        }
    }
    Outcome {
        cents: game.reserved_case_cents,
        cash_out_round: None,
    }
}

pub fn utility_outcome(game: &Trajectory, model: &UtilityModel) -> Result<Outcome, String> {
    for (index, round) in game.rounds.iter().enumerate() {
        let sum = round
            .remaining_cases
            .iter()
            .map(|&v| model.evaluate(v))
            .collect::<Result<Vec<_>, _>>()?
            .iter()
            .sum::<f64>();
        if model.evaluate(round.offer_cents)? >= sum / round.remaining_cases.len() as f64 {
            return Ok(Outcome {
                cents: round.offer_cents,
                cash_out_round: Some(index + 1),
            });
        }
    }
    Ok(Outcome {
        cents: game.reserved_case_cents,
        cash_out_round: None,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::game::generate;
    use rand::{SeedableRng, rngs::SmallRng};
    #[test]
    fn optimized_policy_matches_direct_comparison() {
        let mut rng = SmallRng::seed_from_u64(102);
        for _ in 0..100 {
            let game = generate(&mut rng);
            let thresholds = game.rounds.each_ref().map(|r| threshold(r, -0.015, 0.9));
            let mut gammas: Vec<f64> = (0..=100)
                .map(|i| -0.015 + 0.915 * f64::from(i) / 100.0)
                .collect();
            for t in thresholds {
                if let Threshold::Crossing(x) = t {
                    gammas.extend([x, x - RISK_TOLERANCE / 2.0, x + RISK_TOLERANCE / 2.0]);
                }
            }
            for gamma in gammas {
                let direct = game
                    .rounds
                    .iter()
                    .enumerate()
                    .find(|(_, r)| accepts(r, gamma))
                    .map(|(i, r)| Outcome {
                        cents: r.offer_cents,
                        cash_out_round: Some(i + 1),
                    })
                    .unwrap_or(Outcome {
                        cents: game.reserved_case_cents,
                        cash_out_round: None,
                    });
                assert_eq!(crra_outcome(&game, gamma, &thresholds), direct);
            }
        }
    }
    #[test]
    fn endpoints_ties_ninth_round_and_reserved_payout() {
        let mut game = Trajectory {
            rounds: std::array::from_fn(|_| Round {
                remaining_cases: vec![100],
                offer_cents: 0,
            }),
            reserved_case_cents: 100,
        };
        let declines = [Threshold::AllDecline; 9];
        assert_eq!(
            crra_outcome(&game, 0.0, &declines),
            Outcome {
                cents: 100,
                cash_out_round: None
            }
        );
        assert!(matches!(
            threshold(&game.rounds[0], -0.015, 0.9),
            Threshold::AllDecline
        ));
        game.rounds[8].offer_cents = 100;
        assert!(accepts(&game.rounds[8], 0.0));
        let thresholds = game.rounds.each_ref().map(|r| threshold(r, -0.015, 0.9));
        assert_eq!(
            crra_outcome(&game, 0.0, &thresholds).cash_out_round,
            Some(9)
        );
        game.rounds[0].offer_cents = 101;
        assert!(matches!(
            threshold(&game.rounds[0], -0.015, 0.9),
            Threshold::AllAccept
        ));
    }
}
