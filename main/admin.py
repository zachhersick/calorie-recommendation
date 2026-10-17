from django.contrib import admin

from .models import History, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "age", "sex", "activity_level", "daily_calorie_target"]
    list_filter = ["owner"]


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ["patient", "date", "calories"]
    list_filter = ["patient__owner"]
