from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from . import calories

# Mifflin-St Jeor was validated on adults; inputs outside these bounds are
# either typos or outside the range the equation is meant for.
MIN_AGE, MAX_AGE = 18, 100
MIN_WEIGHT_KG, MAX_WEIGHT_KG = 30, 300
MIN_HEIGHT_CM, MAX_HEIGHT_CM = 120, 230
MAX_DAILY_CALORIES = 20000


class Patient(models.Model):
    SEX_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary (little or no exercise)"),
        ("light", "Light (exercise 1-3 days/week)"),
        ("moderate", "Moderate (exercise 3-5 days/week)"),
        ("active", "Active (exercise 6-7 days/week)"),
        ("very_active", "Very active (hard exercise or physical job)"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patients"
    )
    name = models.CharField(max_length=100)
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(MIN_AGE), MaxValueValidator(MAX_AGE)]
    )
    sex = models.CharField(
        max_length=1,
        choices=SEX_CHOICES,
        help_text="Used by the BMR formula.",
    )
    weight_kg = models.FloatField(
        validators=[MinValueValidator(MIN_WEIGHT_KG), MaxValueValidator(MAX_WEIGHT_KG)]
    )
    height_cm = models.FloatField(
        validators=[MinValueValidator(MIN_HEIGHT_CM), MaxValueValidator(MAX_HEIGHT_CM)]
    )
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    daily_calorie_target = models.PositiveIntegerField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} (age {self.age})"

    def save(self, *args, **kwargs):
        self.daily_calorie_target = round(self.estimate().target)
        super().save(*args, **kwargs)

    def estimate(self):
        return calories.estimate(
            sex=self.sex,
            age=self.age,
            weight_kg=self.weight_kg,
            height_cm=self.height_cm,
            activity_level=self.activity_level,
        )


class History(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="history")
    date = models.DateField()
    calories = models.PositiveIntegerField(validators=[MaxValueValidator(MAX_DAILY_CALORIES)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        verbose_name_plural = "history"
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "date"], name="one_entry_per_patient_per_day"
            ),
        ]

    def __str__(self):
        return f"{self.patient.name} {self.date:%Y-%m-%d}: {self.calories} kcal"
