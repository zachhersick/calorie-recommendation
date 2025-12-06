from django.contrib import admin
from django.urls import path
from . import views
from .views import predict_view

urlpatterns = [
    path('', views.home, name='home'),
    path('new_patient/', views.new_patient, name='new_patient'),
    path("predict/", predict_view, name="predict"),
]