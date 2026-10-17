from django.contrib.auth.decorators import login_not_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PatientForm, TrackCaloriesForm
from .models import Patient


@login_not_required
def home(request):
    return render(request, "index.html")


def _get_patient(request, patient_id):
    return get_object_or_404(Patient, id=patient_id, owner=request.user)


def view_patients(request):
    patients = Patient.objects.filter(owner=request.user)
    return render(request, "view_patients.html", {"patients": patients})


def new_patient(request):
    form = PatientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        patient = form.save(commit=False)
        patient.owner = request.user
        patient.save()
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patient_form.html", {"form": form})


def edit_patient(request, patient_id):
    patient = _get_patient(request, patient_id)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("patient_detail", patient_id=patient.id)
    return render(request, "patient_form.html", {"form": form, "patient": patient})


@require_POST
def delete_patient(request, patient_id):
    _get_patient(request, patient_id).delete()
    return redirect("view_patients")


def patient_detail(request, patient_id):
    patient = _get_patient(request, patient_id)
    return render(request, "patient_detail.html", {
        "patient": patient,
        "estimate": patient.estimate(),
    })


def view_history(request, patient_id):
    patient = _get_patient(request, patient_id)
    history = patient.history.all()
    return render(request, "view_calorie_history.html", {
        "patient": patient,
        "history": history,
        "chart": {
            "labels": [entry.date.isoformat() for entry in history],
            "values": [entry.calories for entry in history],
            "target": patient.daily_calorie_target,
        },
    })


def new_history(request):
    initial = {"patient": request.GET.get("patient")}
    form = TrackCaloriesForm(request.POST or None, initial=initial, owner=request.user)
    if request.method == "POST" and form.is_valid():
        entry = form.save()
        return redirect("view_history", patient_id=entry.patient_id)
    return render(request, "track_calories.html", {"form": form})
