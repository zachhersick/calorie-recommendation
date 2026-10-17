"""Daily energy requirement estimate using the Mifflin-St Jeor equation.

Mifflin MD, St Jeor ST, et al. "A new predictive equation for resting energy
expenditure in healthy individuals." Am J Clin Nutr. 1990;51(2):241-247.
"""

from dataclasses import dataclass

# Standard multipliers applied to BMR to estimate total daily energy expenditure.
ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

SEX_OFFSETS = {
    "M": 5,
    "F": -161,
}

# Mifflin-St Jeor estimates land within 10% of measured resting energy
# expenditure for most adults, so the UI shows this as a plausible range.
UNCERTAINTY = 0.10


@dataclass(frozen=True)
class CalorieEstimate:
    bmr: float
    target: float

    @property
    def low(self):
        return self.target * (1 - UNCERTAINTY)

    @property
    def high(self):
        return self.target * (1 + UNCERTAINTY)


def bmr(*, sex, age, weight_kg, height_cm):
    if sex not in SEX_OFFSETS:
        raise ValueError(f"Unknown sex: {sex!r}")
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + SEX_OFFSETS[sex]


def estimate(*, sex, age, weight_kg, height_cm, activity_level):
    if activity_level not in ACTIVITY_FACTORS:
        raise ValueError(f"Unknown activity level: {activity_level!r}")
    base = bmr(sex=sex, age=age, weight_kg=weight_kg, height_cm=height_cm)
    return CalorieEstimate(bmr=base, target=base * ACTIVITY_FACTORS[activity_level])
