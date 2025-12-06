import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import matplotlib.pyplot as plt
import joblib

#load data
df = pd.read_csv('diet_recommendations_dataset.csv', sep=',')
print(df.columns.tolist())
df.head()

#dropping unused columns
df = df.drop(columns=['Patient_ID', 'Disease_Type', 'Severity', 'Cholesterol_mg/dL', 'Blood_Pressure_mmHg', 'Glucose_mg/dL', 'Dietary_Restrictions', 'Allergies', 'Preferred_Cuisine', 'Adherence_to_Diet_Plan', 'Dietary_Nutrient_Imbalance_Score', 'Diet_Recommendation'])

#categorical encoding
df = pd.get_dummies(df, columns=['Gender', 'Physical_Activity_Level'], drop_first=True)

#split into features and target
X = df.drop('Daily_Caloric_Intake', axis=1)
y = df['Daily_Caloric_Intake']

#standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)


#split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

X_train.shape

#neural network model
model = keras.Sequential([
    layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
    layers.Dropout(0.2),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2),layers.Dense(1)
])

model.compile(optimizer='adam', loss='mean_squared_error', metrics=['mean_absolute_error'])

model.summary()

#train model
history = model.fit(X_train, y_train, epochs=100, batch_size=32, validation_split=0.2)

#plot training/validation mae
plt.plot(history.history['mean_absolute_error'], label='Training Mean Absolute Error')
plt.plot(history.history['val_mean_absolute_error'], label='validation Mean Absolute Error')
plt.title('Model Mean Absolute Error over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Mean Absolute Error')
plt.legend()
plt.grid(True)
plt.show()

#plot training/validation error
plt.plot(history.history['loss'], label='Training Error')
plt.plot(history.history['val_loss'], label='Validation Error')
plt.title('Model Error over Epochs')
plt.xlabel('Epoch')
plt.ylabel('Error')
plt.legend()
plt.grid(True)
plt.show()

#evaluate as regression
test_mse, test_mae = model.evaluate(X_test, y_test, verbose=0)
print(f"Test MSE: {test_mse:.2f}")
print(f"Test MAE: {test_mae:.2f}")

joblib.dump(scaler, 'scaler.pkl')
model.save('calorie_model.h5')

import json
with open('feature_columns.json', 'w') as f:
    json.dump(list(X.columns), f)