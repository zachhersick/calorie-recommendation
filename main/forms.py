from django import forms

from .models import MAX_HEIGHT_CM, MAX_WEIGHT_KG, MIN_HEIGHT_CM, MIN_WEIGHT_KG, History, Patient

KG_PER_LB = 0.45359237
CM_PER_INCH = 2.54


class PatientForm(forms.ModelForm):
    METRIC = "metric"
    IMPERIAL = "imperial"
    UNIT_CHOICES = [
        (METRIC, "Metric (kg, cm)"),
        (IMPERIAL, "Imperial (lb, in)"),
    ]

    units = forms.ChoiceField(choices=UNIT_CHOICES, initial=METRIC, label="Units")
    weight = forms.FloatField(label="Weight", min_value=0)
    height = forms.FloatField(label="Height", min_value=0)

    class Meta:
        model = Patient
        fields = ["name", "age", "sex", "units", "weight", "height", "activity_level"]
        labels = {
            "sex": "Sex",
            "activity_level": "Physical activity level",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("weight", self.instance.weight_kg)
            self.initial.setdefault("height", self.instance.height_cm)

    def clean(self):
        cleaned = super().clean()
        weight, height = cleaned.get("weight"), cleaned.get("height")
        if weight is None or height is None:
            return cleaned
        if cleaned.get("units") == self.IMPERIAL:
            weight *= KG_PER_LB
            height *= CM_PER_INCH

        if not MIN_WEIGHT_KG <= weight <= MAX_WEIGHT_KG:
            self.add_error(
                "weight",
                f"Weight must be between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG} kg "
                f"({MIN_WEIGHT_KG / KG_PER_LB:.0f} to {MAX_WEIGHT_KG / KG_PER_LB:.0f} lb).",
            )
        if not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM:
            self.add_error(
                "height",
                f"Height must be between {MIN_HEIGHT_CM} and {MAX_HEIGHT_CM} cm "
                f"({MIN_HEIGHT_CM / CM_PER_INCH:.0f} to {MAX_HEIGHT_CM / CM_PER_INCH:.0f} in).",
            )

        self.instance.weight_kg = round(weight, 1)
        self.instance.height_cm = round(height, 1)
        return cleaned


class TrackCaloriesForm(forms.ModelForm):
    class Meta:
        model = History
        fields = ["patient", "date", "calories"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Patient.objects.filter(owner=owner)
        self.fields["patient"].empty_label = None
