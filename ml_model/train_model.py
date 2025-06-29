import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

# 1. Load Data
data_path = 'ml_model/sample_pipeline_logs.csv'
df = pd.read_csv(data_path)

# 2. Define features and labels
X = df[['build_time', 'error_count', 'cpu_usage', 'test_pass_rate']]
y = df['status']  # 0 = success, 1 = failure

# 3. Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train Model
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluate Model
y_pred = model.predict(X_test)
print("Classification Report:\n", classification_report(y_test, y_pred))
print("Accuracy:", accuracy_score(y_test, y_pred))

# 6. Save Model
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/model.pkl')
print("Model saved to models/model.pkl")
