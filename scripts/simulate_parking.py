"""Simple simulator to ensure a 'ParkingLogs' sheet exists and append parking rows.

Usage:
  python scripts/simulate_parking.py --spreadsheet-id SPREADSHEET_ID --creds keys/credentials.json --rows 5

Defaults:
  - credentials: keys/credentials.json
  - spreadsheet id: can be passed or left blank to open by name (not recommended)

The script will create the sheet `ParkingLogs` if missing and add header row, then append generated rows.
"""
import argparse
import datetime
import json
import os
import random
import gspread
import time
from typing import List
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
load_dotenv()


DEFAULT_SPREADSHEET_ID = '1fezBLGSZ4N-2R6tUxAqiSGyBRQY5ogexbk0mnYHQ_QA'
PARKING_SHEET_NAME = 'ParkingLogs'
CREDS=os.getenv('SERVICE_ACCOUNT_CREDS')


def auth_gspread(creds_path: str):
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    return client


def ensure_sheet(client: gspread.Client, spreadsheet_id: str, sheet_name: str, headers: List[str]):
    ss = client.open_by_key(spreadsheet_id)
    try:
        sheet = ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        sheet = ss.add_worksheet(title=sheet_name, rows="1000", cols=str(len(headers)))
    # Ensure headers
    try:
        values = sheet.get_all_values()
    except Exception:
        values = []
    if values == [] or (len(values) > 0 and len(values[0]) == 0):
        sheet.insert_row(headers, index=1)
    return sheet


def generate_row(location: str = "Malabe") -> List:
    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    # Simulate device id
    device_id = random.choice([f'ESP32_{i:02d}' for i in range(1, 11)])
    distance = round(random.uniform(5.0, 300.0), 2)
    vehicle_detected = 'YES' if distance < 200 else 'NO'
    duration = random.randint(30, 3600) if vehicle_detected == 'YES' else 0
    # RSSI (signal strength) in dBm
    rssi = random.randint(-90, -30)
    # Random-ish GPS around approximate Colombo coords (small jitter)
    base_lat, base_lon = 6.9271, 79.8612
    lat = round(base_lat + random.uniform(-0.01, 0.01), 6)
    lon = round(base_lon + random.uniform(-0.01, 0.01), 6)
    status = 'OCCUPIED' if vehicle_detected == 'YES' else 'VACANT'
    received_at = datetime.datetime.utcnow().isoformat()
    client_ip = ''
    raw = json.dumps({
        'timestamp': now,
        'device': device_id,
        'location': location,
        'distance': distance,
        'vehicle_detected': vehicle_detected,
        'parking_duration': duration,
        'rssi': rssi,
        'lat': lat,
        'lon': lon,
        'status': status
    })
    # Columns: Time, Device_ID, Location, Distance_cm, Vehicle_Detected, Parking_Duration_s, RSSI_dBm, Latitude, Longitude, Status, Received_At, Raw_Params
    return [now, device_id, location, distance, vehicle_detected, duration, f"{rssi} dBm", lat, lon, status, received_at, raw]


def append_rows(sheet: gspread.Worksheet, rows: List[List], pause: float = 0.0):
    for r in rows:
        sheet.append_row(r, value_input_option='USER_ENTERED')
        if pause:
            time.sleep(pause)


def main():
    p = argparse.ArgumentParser(description='Append simulated parking rows to ParkingLogs sheet')
    p.add_argument('--spreadsheet-id', default=DEFAULT_SPREADSHEET_ID)
    p.add_argument('--creds', default=CREDS)
    p.add_argument('--rows', type=int, default=50, help='number of random rows to append')
    p.add_argument('--location', default='Colombo_Parking_01')
    p.add_argument('--interval', type=float, default=0.0, help='seconds between appends')
    args = p.parse_args()
    client = auth_gspread(args.creds)
    headers = ['Time', 'Device_ID', 'Location', 'Distance_cm', 'Vehicle_Detected', 'Parking_Duration_s', 'RSSI_dBm', 'Latitude', 'Longitude', 'Status', 'Received_At', 'Raw_Params']
    sheet = ensure_sheet(client, args.spreadsheet_id, PARKING_SHEET_NAME, headers)

    rows = [generate_row(args.location) for _ in range(args.rows)]
    append_rows(sheet, rows, pause=args.interval)
    print(f'Appended {len(rows)} rows to {PARKING_SHEET_NAME} in spreadsheet {args.spreadsheet_id}')


if __name__ == '__main__':
    main()
