from django.shortcuts import render, redirect, get_object_or_404
import time
from .forms import PatientForm
from .ml_predict import predict_daily_caloric_intake
from main.models import Patient

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
