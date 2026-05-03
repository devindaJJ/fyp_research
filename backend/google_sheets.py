import os
import gspread
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()


class GoogleSheetsHandler:
    def __init__(self):
        self.setup_google_sheets()

    def setup_google_sheets(self):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets"
        ]

        creds_path = os.getenv("SERVICE_ACCOUNT_CREDS")

        if not creds_path:
            creds_path = os.path.join(os.path.dirname(__file__), "keys", "credentials.json")

        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"credentials.json not found: {creds_path}")

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=scope
        )

        self.client = gspread.authorize(creds)

        spreadsheet_id = os.getenv("SHEET_ID")

        if not spreadsheet_id:
            spreadsheet_id = "1bJKg407L6pQ6TA5aKDY9JZd5s-5ICCdmflZB6BEJbZE"

        self.spreadsheet = self.client.open_by_key(spreadsheet_id)

        try:
            self.sheet = self.spreadsheet.worksheet("AccidentLogs")
        except Exception:
            self.sheet = self.spreadsheet.sheet1

        self.ensure_accident_headers()

    def ensure_accident_headers(self):
        headers = ["date", "Latitude", "Longitude", "Vibration", "Distance"]

        values = self.sheet.get_all_values()

        if not values:
            # Sheet is completely empty — safe to insert headers
            self.sheet.append_row(headers)

        elif values[0] != headers:
            # FIX: Original code deleted row 1 unconditionally and reinserted headers,
            # which destroyed any real data sitting in row 1 if the header row was
            # missing or mismatched. Now we only insert the header row at position 1
            # without deleting anything, which pushes existing rows down safely.
            self.sheet.insert_row(headers, 1)

    def append_accident_record(self, record):
        try:
            row = [
                record.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                record.get("Latitude", ""),
                record.get("Longitude", ""),
                record.get("Vibration", ""),
                record.get("Distance", "")
            ]
            self.sheet.append_row(row, value_input_option="USER_ENTERED")
            return True

        except Exception as e:
            print(f"Error appending accident record: {e}")
            return False

    def get_accident_records(self):
        try:
            records = self.sheet.get_all_records()

            result = []
            for record in records:
                result.append({
                    "timestamp": record.get("date", ""),
                    "latitude": record.get("Latitude", ""),
                    "longitude": record.get("Longitude", ""),
                    "vibration": record.get("Vibration", ""),
                    "distance": record.get("Distance", "")
                })

            return result

        except Exception as e:
            print(f"Error reading accident records: {e}")
            return []

    def get_parking_data(self):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.sheet

            records = sheet.get_all_records()
            processed_data = []

            for record in records:
                timestamp = record.get("Timestamp") or record.get("Time") or record.get("time")
                distance = record.get("Distance") or record.get("Distance_cm") or record.get("distance")
                status = record.get("Status") or record.get("status") or ""

                if not timestamp or distance is None:
                    continue

                try:
                    distance_val = float(distance)
                except Exception:
                    distance_val = 0.0

                processed_data.append({
                    "timestamp": timestamp,
                    "distance": distance_val,
                    "status": status,
                    "location": record.get("Location") or record.get("location") or "Unknown",
                    "device_id": record.get("Device_ID") or record.get("DeviceId") or record.get("device") or None,
                    "rssi": record.get("RSSI_dBm") or record.get("rssi") or None,
                    "latitude": record.get("Latitude") or record.get("lat") or None,
                    "longitude": record.get("Longitude") or record.get("lon") or None,
                    "raw": record
                })

            return processed_data[-50:]

        except Exception as e:
            print(f"Error reading Google Sheets: {e}")
            return []

    def get_violations_since(self, since_time):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.sheet

            records = sheet.get_all_records()
            violations = []

            for record in records:
                status = record.get("Status") or record.get("status") or ""
                distance = record.get("Distance") or record.get("Distance_cm") or record.get("distance")
                timestamp = record.get("Timestamp") or record.get("Time") or None

                try:
                    distance_val = float(distance)
                except Exception:
                    distance_val = 9999

                if status == "OCCUPIED" and distance_val < 10:
                    try:
                        record_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        try:
                            record_time = datetime.fromisoformat(timestamp)
                        except Exception:
                            continue

                    if record_time >= since_time:
                        violations.append({
                            "timestamp": timestamp,
                            "location": record.get("Location") or record.get("location") or "Unknown",
                            "distance": distance_val,
                            "device_id": record.get("Device_ID") or record.get("device") or None,
                            "priority": "HIGH" if distance_val < 5 else "MEDIUM"
                        })

            return violations

        except Exception as e:
            print(f"Error getting violations: {e}")
            return []

    def get_system_statistics(self):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.sheet

            records = sheet.get_all_records()

            if not records:
                return {}

            df = pd.DataFrame(records)

            total_records = len(df)
            status_col = "Status" if "Status" in df.columns else ("status" if "status" in df.columns else None)
            distance_col = "Distance" if "Distance" in df.columns else (
                "Distance_cm" if "Distance_cm" in df.columns else (
                    "distance" if "distance" in df.columns else None
                )
            )

            if status_col:
                available_spots = len(df[df[status_col] == "AVAILABLE"])
                occupied_spots = len(df[df[status_col] == "OCCUPIED"])
            else:
                available_spots = 0
                occupied_spots = 0

            if status_col and distance_col:
                violation_count = len(
                    df[(df[status_col] == "OCCUPIED") & (df[distance_col].astype(float) < 10)]
                )
            else:
                violation_count = 0

            return {
                "total_records": total_records,
                "available_spots": available_spots,
                "occupied_spots": occupied_spots,
                "violation_count": violation_count,
                "utilization_rate": round((occupied_spots / total_records) * 100, 2) if total_records > 0 else 0
            }

        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}

    def get_device_health(self):
        return [
            {
                "device_id": "SN-001",
                "location": "Main Gate A1",
                "status": "online",
                "battery": 85,
                "last_update": datetime.now().isoformat()
            },
            {
                "device_id": "SN-002",
                "location": "Street B2",
                "status": "offline",
                "battery": 15,
                "last_update": (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]

    def append_parking_record(self, record):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.spreadsheet.add_worksheet(
                    title="ParkingLogs",
                    rows="2000",
                    cols="20"
                )

            headers = [
                "Time",
                "Device_ID",
                "Location",
                "Distance_cm",
                "Vehicle_Detected",
                "Parking_Duration_s",
                "RSSI_dBm",
                "Latitude",
                "Longitude",
                "Status",
                "Received_At",
                "Raw_Params"
            ]

            values = sheet.get_all_values()

            if not values:
                sheet.insert_row(headers, index=1)

            row = [
                record.get("timestamp") or record.get("Time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                record.get("device") or record.get("Device_ID") or record.get("device_id") or "",
                record.get("location") or record.get("Location") or "",
                record.get("distance") or record.get("Distance") or record.get("Distance_cm") or "",
                record.get("vehicle_detected") or record.get("Vehicle_Detected") or record.get("vehicle") or "",
                record.get("parking_duration") or record.get("Parking_Duration_s") or record.get("duration") or "",
                record.get("rssi") or record.get("RSSI_dBm") or "",
                record.get("lat") or record.get("Latitude") or "",
                record.get("lon") or record.get("Longitude") or "",
                record.get("Status") or record.get("status") or "",
                datetime.now().isoformat(),
                str(record)
            ]

            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True

        except Exception as e:
            print(f"Error appending parking record: {e}")
            return False

    def append_action(self, action):
        try:
            try:
                sheet = self.spreadsheet.worksheet("Actions")
            except Exception:
                sheet = self.spreadsheet.add_worksheet(
                    title="Actions",
                    rows="1000",
                    cols="10"
                )

            headers = ["Time", "Device_ID", "Action", "Note", "User", "Recorded_At"]

            values = sheet.get_all_values()

            if not values:
                sheet.insert_row(headers, index=1)

            row = [
                action.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action.get("device_id") or action.get("device") or "",
                action.get("action") or "",
                action.get("note") or "",
                action.get("user") or "",
                datetime.now().isoformat()
            ]

            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True

        except Exception as e:
            print(f"Error appending action record: {e}")
            return False