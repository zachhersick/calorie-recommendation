from django.shortcuts import render
from .forms import PatientForm
from .ml_predict import predict_daily_caloric_intake

# Create your views here.
def home(request):
    return render(request, 'index.html')

def new_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            new_team = form.save(commit=False)
            new_team.userOwner = request.user
            new_team.save()
            
            context = {
                'team_name': request.POST.get("name"),
                'team_city': request.POST.get("city")
            }
            return render(request, 'conf.html', context)
            # return redirect('all_teams')
    
    form = PatientForm()
    context = {'form': form}
    return render(request, 'new_patient.html', context)

def predict_view(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            prediction = predict_daily_caloric_intake(patient)

            return render(request, "prediction_result.html", {
                "patient": patient,
                "prediction": prediction,
            })

    else:
        form = PatientForm()

    return render(request, "predict.html", {"form": form})
