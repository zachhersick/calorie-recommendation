from django import forms
from .models import Patient, History

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'name',
            'age',
            'gender',
            'weight_kg',
            'height_cm',
            'physical_activity_level',
            'weekly_exercise_hours',
        ]

        labels = {
            'name': 'Name',
            'age': 'Age',
            'gender': 'Gender',
            'weight_kg': 'Weight (kg)',
            'height_cm': 'Height (cm)',
            'physical_activity_level': 'Physical Activity Level',
            'weekly_exercise_hours': 'Weekly Exercise Hours',
        }

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'physical_activity_level': forms.Select(attrs={'class': 'form-control'}),
            'weekly_exercise_hours': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
class TrackCaloriesForm(forms.ModelForm):
    class Meta:
        model = History
        fields = [
            'day',
            'month',
            'year',
            'calories',
        ]

        labels = {
            'day': 'Day',
            'month': 'Month',
            'year': 'Year',
            'calories': 'Calories',
        }

        widgets = {
            'day': forms.NumberInput(attrs={'class': 'form-control'}),
            'month': forms.NumberInput(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control'}),
        }