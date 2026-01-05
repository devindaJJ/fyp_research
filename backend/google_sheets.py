import gspread
import os
import datetime
import time
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

class GoogleSheetsHandler:
    def __init__(self):
        self.setup_google_sheets()
    
    def setup_google_sheets(self):
        # Google Sheets API setup
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Download service account JSON from Google Cloud Console
        creds = Credentials.from_service_account_file(
            os.getenv("SERVICE_ACCOUNT_CREDS"), scopes=scope
        )
        
        self.client = gspread.authorize(creds)
        
        # Open your Google Sheet - prefer SPREADSHEET_ID env var when present
        spreadsheet_id = os.getenv('SHEET_ID')
        spreadsheet_name = os.getenv('SPREADSHEET_NAME')

        if spreadsheet_id:
            try:
                self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            except Exception as e:
                raise RuntimeError(f"Failed to open spreadsheet by id '{spreadsheet_id}': {e}\nEnsure SPREADSHEET_ID is correct and the service account has access.")
        else:
            try:
                self.spreadsheet = self.client.open(spreadsheet_name)
            except Exception as e:
                raise RuntimeError(
                    f"Spreadsheet named '{spreadsheet_name}' not found: {e}\n" +
                    "Either create a spreadsheet with that name and share it with the service account, " +
                    "or set the SPREADSHEET_ID environment variable to the spreadsheet key."
                )

        # Use a default worksheet for legacy reads but prefer named sheets when available
        try:
            self.sheet = self.spreadsheet.worksheet('AccidentLogs')
        except Exception:
            try:
                self.sheet = self.spreadsheet.sheet1
            except Exception:
                # create a default sheet if everything else fails
                self.sheet = self.spreadsheet.add_worksheet(title='AccidentLogs', rows="1000", cols="20")
    
    def get_parking_data(self):
        """Get all parking data from Google Sheets"""
        try:
            # Try to read from ParkingLogs sheet first if present
            try:
                sheet = self.spreadsheet.worksheet('ParkingLogs')
            except Exception:
                sheet = self.sheet

            records = sheet.get_all_records()

            # Normalize and process data from different header conventions
            processed_data = []
            for record in records:
                # Determine timestamp field
                timestamp = record.get('Timestamp') or record.get('Time') or record.get('time')
                # Determine distance field
                distance = record.get('Distance') or record.get('Distance_cm') or record.get('distance')
                status = record.get('Status') or record.get('status') or ''
                if not timestamp or distance is None:
                    continue

                # Normalize numeric distance
                try:
                    distance_val = float(distance)
                except Exception:
                    try:
                        distance_val = float(str(distance).split()[0])
                    except Exception:
                        distance_val = 0.0

                processed_data.append({
                    'timestamp': timestamp,
                    'distance': distance_val,
                    'status': status,
                    'location': record.get('Location') or record.get('location') or 'Unknown',
                    'device_id': record.get('Device_ID') or record.get('DeviceId') or record.get('device') or None,
                    'rssi': record.get('RSSI_dBm') or record.get('rssi') or None,
                    'latitude': record.get('Latitude') or record.get('lat') or None,
                    'longitude': record.get('Longitude') or record.get('lon') or None,
                    'raw': record
                })

            return processed_data[-50:]
        
        except Exception as e:
            print(f"Error reading Google Sheets: {e}")
            return []
    
    def get_violations_since(self, since_time):
        """Get violations since specified time"""
        try:
            # Read from ParkingLogs when possible
            try:
                sheet = self.spreadsheet.worksheet('ParkingLogs')
            except Exception:
                sheet = self.sheet

            records = sheet.get_all_records()
            violations = []

            for record in records:
                status = record.get('Status') or record.get('status') or ''
                distance = record.get('Distance') or record.get('Distance_cm') or record.get('distance')
                timestamp = record.get('Timestamp') or record.get('Time') or None

                try:
                    distance_val = float(distance)
                except Exception:
                    distance_val = 9999

                if status == 'OCCUPIED' and distance_val < 10:
                    # Attempt to parse timestamp safely
                    try:
                        record_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        try:
                            record_time = datetime.fromisoformat(timestamp)
                        except Exception:
                            continue

                    if record_time >= since_time:
                        violations.append({
                            'timestamp': timestamp,
                            'location': record.get('Location') or record.get('location') or 'Unknown',
                            'distance': distance_val,
                            'device_id': record.get('Device_ID') or record.get('device') or None,
                            'priority': 'HIGH' if distance_val < 5 else 'MEDIUM'
                        })

            return violations
        
        except Exception as e:
            print(f"Error getting violations: {e}")
            return []
    
    def get_system_statistics(self):
        """Calculate system statistics"""
        try:
            try:
                sheet = self.spreadsheet.worksheet('ParkingLogs')
            except Exception:
                sheet = self.sheet
            records = sheet.get_all_records()
            if not records:
                return {}
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(records)
            
            # Calculate statistics
            total_records = len(df)
            # handle possible column name differences
            status_col = 'Status' if 'Status' in df.columns else ('status' if 'status' in df.columns else None)
            distance_col = 'Distance' if 'Distance' in df.columns else ('Distance_cm' if 'Distance_cm' in df.columns else ('distance' if 'distance' in df.columns else None))

            if status_col:
                available_spots = len(df[df[status_col] == 'AVAILABLE'])
                occupied_spots = len(df[df[status_col] == 'OCCUPIED'])
            else:
                available_spots = 0
                occupied_spots = 0

            if status_col and distance_col:
                violation_count = len(df[(df[status_col] == 'OCCUPIED') & (df[distance_col].astype(float) < 10)])
            else:
                violation_count = 0
            
            return {
                'total_records': total_records,
                'available_spots': available_spots,
                'occupied_spots': occupied_spots,
                'violation_count': violation_count,
                'utilization_rate': round((occupied_spots / total_records) * 100, 2) if total_records > 0 else 0
            }
        
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}
    
    def get_device_health(self):
        """Get device health status (mock data - extend based on your actual data)"""
        # This would typically come from a separate sheet or database
        return [
            {
                'device_id': 'SN-001',
                'location': 'Main Gate A1',
                'status': 'online',
                'battery': 85,
                'last_update': datetime.now().isoformat()
            },
            {
                'device_id': 'SN-002', 
                'location': 'Street B2',
                'status': 'offline',
                'battery': 15,
                'last_update': (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]

    def append_parking_record(self, record: dict):
        """Append a single parking record to ParkingLogs sheet, creating the sheet if missing.

        Expected record keys (flexible): timestamp/Time, device/device_id, location, distance/Distance_cm,
        vehicle_detected, parking_duration, rssi/RSSI_dBm, lat/Latitude, lon/Longitude, Status
        """
        try:
            # Get or create sheet
            try:
                sheet = self.spreadsheet.worksheet('ParkingLogs')
            except Exception:
                sheet = self.spreadsheet.add_worksheet(title='ParkingLogs', rows="2000", cols="20")

            # Ensure headers
            headers = ['Time', 'Device_ID', 'Location', 'Distance_cm', 'Vehicle_Detected', 'Parking_Duration_s', 'RSSI_dBm', 'Latitude', 'Longitude', 'Status', 'Received_At', 'Raw_Params']
            try:
                values = sheet.get_all_values()
            except Exception:
                values = []
            if values == [] or (len(values) > 0 and len(values[0]) == 0):
                sheet.insert_row(headers, index=1)

            # Map record to columns
            time_val = record.get('timestamp') or record.get('Time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            device_id = record.get('device') or record.get('Device_ID') or record.get('device_id') or ''
            location = record.get('location') or record.get('Location') or ''
            distance = record.get('distance') or record.get('Distance') or record.get('Distance_cm') or ''
            vehicle = record.get('vehicle_detected') or record.get('Vehicle_Detected') or record.get('vehicle') or ''
            duration = record.get('parking_duration') or record.get('Parking_Duration_s') or record.get('duration') or ''
            rssi = record.get('rssi') or record.get('RSSI_dBm') or ''
            lat = record.get('lat') or record.get('Latitude') or ''
            lon = record.get('lon') or record.get('Longitude') or ''
            status = record.get('Status') or record.get('status') or ''
            received = datetime.now().isoformat()
            raw = record

            row = [time_val, device_id, location, distance, vehicle, duration, rssi, lat, lon, status, received, str(raw)]
            sheet.append_row(row, value_input_option='USER_ENTERED')
            return True
        except Exception as e:
            print(f"Error appending parking record: {e}")
            return False

    def append_action(self, action: dict):
        """Append an action/operation to Actions sheet (dispatch, resolve).

        action expected keys: timestamp, device_id, action, note, user
        """
        try:
            try:
                sheet = self.spreadsheet.worksheet('Actions')
            except Exception:
                sheet = self.spreadsheet.add_worksheet(title='Actions', rows="1000", cols="10")

            headers = ['Time', 'Device_ID', 'Action', 'Note', 'User', 'Recorded_At']
            try:
                values = sheet.get_all_values()
            except Exception:
                values = []
            if values == [] or (len(values) > 0 and len(values[0]) == 0):
                sheet.insert_row(headers, index=1)

            time_val = action.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            device_id = action.get('device_id') or action.get('device') or ''
            act = action.get('action') or ''
            note = action.get('note') or ''
            user = action.get('user') or ''
            recorded = datetime.now().isoformat()

            row = [time_val, device_id, act, note, user, recorded]
            sheet.append_row(row, value_input_option='USER_ENTERED')
            return True
        except Exception as e:
            print(f"Error appending action record: {e}")
            return False