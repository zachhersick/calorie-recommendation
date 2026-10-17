from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("patients/", views.view_patients, name="view_patients"),
    path("patients/new/", views.new_patient, name="new_patient"),
    path("patients/<int:patient_id>/", views.patient_detail, name="patient_detail"),
    path("patients/<int:patient_id>/edit/", views.edit_patient, name="edit_patient"),
    path("patients/<int:patient_id>/delete/", views.delete_patient, name="delete_patient"),
    path("patients/<int:patient_id>/history/", views.view_history, name="view_history"),
    path("track/", views.new_history, name="track_calories"),
]
