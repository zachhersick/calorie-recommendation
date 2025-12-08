from django.contrib import admin
from django.urls import path
from . import views
from .views import predict_result

urlpatterns = [
    path('', views.home, name='home'),
    path('patients/new/', views.new_patient, name='new_patient'),
    path('predict/<int:patient_id>/', views.predict_result, name='predict_result'),
    path('patients/view/', views.view_patients, name='view_patients'),
    path('patients/history/<int:patient_id>/', views.view_history, name='view_history'),
    path('patients/track/', views.new_history, name='track_calories')
]