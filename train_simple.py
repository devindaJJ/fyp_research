import os
import logging
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import joblib
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()

logging.info("TEACHING COMPUTER TO RECOGNIZE ACCIDENTS")
logging.info("="*50)

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_file(
    os.getenv('SERVICE_ACCOUNT_CREDS'),
    scopes=scopes
)
client = gspread.authorize(creds)

sheet_id = os.getenv('SHEET_ID')
sheet = client.open_by_key(sheet_id)
worksheet = sheet.worksheet('AccidentLogs')

# Convert to DataFrame
df = pd.DataFrame(worksheet.get_all_records())
logging.info(f"DataFrame columns: {df.columns.tolist()}")
logging.info(f"Using YOUR {len(df)} samples from Google Sheets")

# Convert text values to numbers
df['Impact Detected'] = df['Impact Detected'].map({'NO': 0, 'YES': 1})
df['Distance Violation'] = df['Distance Violation'].map({'NO': 0, 'YES': 1})

# Convert Alert Level if it's text (e.g., 'LOW', 'MEDIUM', 'HIGH')
if df['Alert Level'].dtype == 'object':
    df['Alert Level'] = df['Alert Level'].map({'NORMAL': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4})

logging.info(f"Converted text columns to numbers")

# Common features for all models
features = df[['Distance (cm)', 'Impact Detected', 'Total Impacts']]

# Predict Distance Violation 
logging.info("\nTraining Model 1: Distance Violation Detector")
labels_distance = df['Distance Violation']
model_distance = DecisionTreeClassifier(max_depth=3)
model_distance.fit(features, labels_distance)
logging.info("Saved: model_distance_violation.pkl")

# Predict Impact Detected 
logging.info("\nTraining Model 2: Impact/Accident Detector")
labels_impact = df['Impact Detected']
model_impact = DecisionTreeClassifier(max_depth=3)
model_impact.fit(features, labels_impact)
logging.info("Saved: model_impact_detected.pkl")

# Predict Alert Level
logging.info("\nTraining Model 3: Alert Level Predictor")
labels_alert = df['Alert Level']
model_alert = DecisionTreeClassifier(max_depth=3)
model_alert.fit(features, labels_alert)
logging.info("Saved: model_alert_level.pkl")

joblib.dump(model_distance, 'src/models/trained/model_distance_violation.pkl')
joblib.dump(model_impact, 'src/models/trained/model_impact_detected.pkl')
joblib.dump(model_alert, 'src/models/trained/model_alert_level.pkl')

logging.info("\n" + "="*50)
logging.info("TESTING ALL MODELS:")
logging.info("="*50)

test_cases = [
    [35, 1, 2],   # Close + impact + 2 total impacts
    [150, 1, 1],  # Far + impact + 1 total impact
    [180, 0, 0],  # Far + no impact + 0 total impacts
]

for i, test in enumerate(test_cases, 1):
    logging.info(f"\nTest Case {i}: Distance={test[0]}cm, Impact={test[1]}, Total Impacts={test[2]}")
    
    pred_distance = model_distance.predict([test])[0]
    pred_impact = model_impact.predict([test])[0]
    pred_alert = model_alert.predict([test])[0]
    
    logging.info(f"  → Distance Violation: {'YES' if pred_distance == 1 else 'NO'}")
    logging.info(f"  → Impact Detected: {'YES' if pred_impact == 1 else 'NO'}")
    logging.info(f"  → Alert Level: {pred_alert}")

logging.info("\n" + "="*50)
logging.info("ALL MODELS TRAINED SUCCESSFULLY!")