from django.shortcuts import render, redirect, get_object_or_404
import time
from .forms import PatientForm, TrackCaloriesForm
from .ml_predict import predict_daily_caloric_intake
from main.models import Patient, History

# Create your views here.
def home(request):
    return render(request, 'index.html')

def new_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            return redirect('view_patients')
    else:
        form = PatientForm()

    return render(request, 'new_patient.html', {'form': form})

def predict_result(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    prediction = predict_daily_caloric_intake(patient)
    
    context = {
        'patient': patient,
        'prediction': prediction
    }
    
    return render(request, 'prediction_result.html', context)

def view_patients(request):
    patients = Patient.objects.all()
    return render(request, 'view_patients.html', {'patients': patients})

def view_history(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    history = History.objects.filter(patient=patient).order_by("year", "month", "day")

    labels = [f"{h.month}/{h.day}/{h.year}" for h in history]
    values = [h.calories for h in history]

    return render(request, 'view_calorie_history.html', {
        'patient': patient,
        'history': history,
        'labels': labels,
        'values': values,
    })

def new_history(request):
    if request.method == 'POST':
        form = TrackCaloriesForm(request.POST)

        patient_id = request.POST.get('patient_id')
        if not patient_id:
            return redirect('track_calories')  # fallback

        patient = get_object_or_404(Patient, id=patient_id)

        if form.is_valid():
            entry = form.save(commit=False)
            entry.patient = patient
            entry.save()
            return redirect('view_history', patient_id=patient.id)

    else:
        form = TrackCaloriesForm()

    patients = Patient.objects.all()
    return render(request, 'track_calories.html', {
        'form': form,
        'patients': patients
    })




