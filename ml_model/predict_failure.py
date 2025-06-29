import joblib
import pandas as pd

# Load trained model
model = joblib.load('models/model.pkl')

# Example input data as dictionary
example_data = pd.DataFrame([{
    'build_time': 250,
    'error_count': 7,
    'cpu_usage': 60.0,
    'test_pass_rate': 0.70
}])

# Predict
prediction = model.predict(example_data)[0]
probability = model.predict_proba(example_data)[0][1]  # Probability of failure (1)

print(f"Predicted Status: {'Failure' if prediction == 1 else 'Success'}")
print(f"Failure Probability: {round(probability * 100, 2)}%")
