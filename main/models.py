from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    ACTIVITY_CHOICES = [
        ('Sedentary', 'Sedentary'),
        ('Moderate', 'Moderate'),
        ('Active', 'Active'),
    ]
    
    name = models.CharField(default='user')
    age = models.IntegerField()
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        null=True,
        blank=True
    )
    weight_kg = models.FloatField()
    height_cm = models.IntegerField()
    physical_activity_level = models.CharField(
        max_length=50,
        choices=ACTIVITY_CHOICES,
        null=True,
        blank=True
    )
    weekly_exercise_hours = models.FloatField()
    
    def __str__(self):
        return f"Patient {self.name} — Age: {self.age}, Gender: {self.gender}"