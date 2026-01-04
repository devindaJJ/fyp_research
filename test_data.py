import os
import random
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

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

# Generate test data
test_data = []
base_time = datetime.now()

for i in range(100): 
    timestamp = (base_time - timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S')
    device_id = f"ESP32_{random.randint(1, 5):03d}"
    distance = random.randint(20, 200)
    
    # Realistic scenarios
    if distance < 50:  # Close distance
        impact = 'YES' if random.random() > 0.3 else 'NO'
        dist_violation = 'YES'
        total_impacts = random.randint(1, 5) if impact == 'YES' else 0
        alert = 'HIGH' if impact == 'YES' else 'MEDIUM'
    elif distance < 100:  # Medium distance
        impact = 'YES' if random.random() > 0.7 else 'NO'
        dist_violation = 'NO'
        total_impacts = random.randint(0, 2)
        alert = 'MEDIUM' if impact == 'YES' else 'LOW'
    else:  # Far distance
        impact = 'NO'
        dist_violation = 'NO'
        total_impacts = 0
        alert = 'NORMAL'
    
    wifi = random.randint(-80, -40)
    lat = 6.9271 + random.uniform(-0.01, 0.01) 
    lon = 79.8612 + random.uniform(-0.01, 0.01)
    
    row = [
        timestamp,
        device_id,
        distance,
        impact,
        dist_violation,
        total_impacts,
        wifi,
        timestamp,
        lat,
        lon,
        'Active',
        alert
    ]
    test_data.append(row)

worksheet.append_rows(test_data)
print(f"Added {len(test_data)} test records to AccidentLogs!")
print("You can now run train_simple.py again")