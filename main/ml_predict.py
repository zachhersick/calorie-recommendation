import numpy as np
import json
import joblib
import tensorflow as tf
from django.conf import settings
import os

# Paths
BASE_DIR = settings.BASE_DIR
MODEL_PATH = os.path.join(BASE_DIR, 'calorie_model.h5')
SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')
FEATURES_PATH = os.path.join(BASE_DIR, 'feature_columns.json')

# Load model + scaler once
model = tf.keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

with open(FEATURES_PATH, 'r') as f:
    FEATURE_COLUMNS = json.load(f)


def patient_to_feature_vector(patient):
    """
    Convert DB model instance -> correctly ordered single sample
    """
    base = {}

    # ⬇ matches EXACT JSON order
    base["Age"] = patient.age
    base["Weight_kg"] = patient.weight_kg
    base["Height_cm"] = patient.height_cm
    base["BMI"] = patient.bmi
    base["Weekly_Exercise_Hours"] = patient.weekly_exercise_hours

    # categorical: GENDER
    # FEATURE_COLUMNS contains: "Gender_Male"
    base["Gender_Male"] = 1 if patient.gender == "M" else 0

    # categorical: ACTIVITY LEVEL
    # model expects EXACTLY:
    #   Physical_Activity_Level_Moderate
    #   Physical_Activity_Level_Sedentary
    # base class is likely Active or something not included
    base["Physical_Activity_Level_Moderate"] = 0
    base["Physical_Activity_Level_Sedentary"] = 0

    # set matching dummy
    patient_level = patient.physical_activity_level.strip()

    if patient_level == "Moderate":
        base["Physical_Activity_Level_Moderate"] = 1
    elif patient_level == "Sedentary":
        base["Physical_Activity_Level_Sedentary"] = 1

    # IMPORTANT:
    # if patient enters "Active" or anything else → remains baseline (all zeros)

    # Order matters → follow FEATURE_COLUMNS
    vector = [base[col] for col in FEATURE_COLUMNS]

    return np.array(vector, dtype=float).reshape(1, -1)


def predict_daily_caloric_intake(patient):
    """
    returns predicted calorie intake for a patient record
    """
    x = patient_to_feature_vector(patient)
    x_scaled = scaler.transform(x)
    pred = model.predict(x_scaled, verbose=0)
    return float(pred[0][0])

