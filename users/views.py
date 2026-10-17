from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render

from .forms import SignUpForm


@login_not_required
def signup(request):
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("view_patients")
    return render(request, "registration/signup.html", {"form": form})
