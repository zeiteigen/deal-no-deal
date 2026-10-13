//! CRRA and shared, monotone piecewise-linear utility models.
use serde::{Deserialize, Serialize};

pub fn crra(gamma: f64, cents: u32) -> f64 {
    f64::from(cents).powf(1.0 - gamma) / (1.0 - gamma)
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Point {
    pub cash_cents: u32,
    pub utility: f64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct UtilityModel {
    pub schema_version: u32,
    pub name: String,
    pub points: Vec<Point>,
}

impl UtilityModel {
    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != 1 || self.name.trim().is_empty() || self.points.len() < 2 {
            return Err(
                "Utility requires schema_version 1, a name, and at least two points".into(),
            );
        }
        if self.points.iter().any(|p| !p.utility.is_finite())
            || self
                .points
                .windows(2)
                .any(|w| w[0].cash_cents >= w[1].cash_cents || w[0].utility > w[1].utility)
        {
            return Err(
                "Utility cash must strictly increase and finite utilities must not decrease".into(),
            );
        }
        Ok(())
    }

    pub fn evaluate(&self, cents: u32) -> Result<f64, String> {
        let first = self.points.first().ok_or("Utility has no points")?;
        let last = self.points.last().ok_or("Utility has no points")?;
        if cents < first.cash_cents || cents > last.cash_cents {
            return Err(format!(
                "Cash {cents} cents lies outside utility model domain"
            ));
        }
        if cents == first.cash_cents {
            return Ok(first.utility);
        }
        let index = self.points.partition_point(|p| p.cash_cents < cents);
        let low = &self.points[index - 1];
        let high = &self.points[index];
        let fraction =
            f64::from(cents - low.cash_cents) / f64::from(high.cash_cents - low.cash_cents);
        Ok(low.utility + fraction * (high.utility - low.utility))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn interpolation_and_validation() {
        let mut model = UtilityModel {
            schema_version: 1,
            name: "test".into(),
            points: vec![
                Point {
                    cash_cents: 0,
                    utility: 0.0,
                },
                Point {
                    cash_cents: 100,
                    utility: 10.0,
                },
            ],
        };
        assert!(model.validate().is_ok());
        assert_eq!(model.evaluate(25).unwrap(), 2.5);
        assert_eq!(model.evaluate(100).unwrap(), 10.0);
        assert!(model.evaluate(101).is_err());
        model.points[1].utility = -1.0;
        assert!(model.validate().is_err());
    }
}
