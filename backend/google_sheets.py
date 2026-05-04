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

        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
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
            self.sheet.append_row(headers)
        elif values[0] != headers:
            self.sheet.insert_row(headers, 1)

    # ─── Date/time helpers ────────────────────────────────────────────────────

    @staticmethod
    def _serial_to_datetime_str(value):
        """
        Convert a Google Sheets date serial number to a datetime string.

        Google Sheets stores dates as the number of days since December 30, 1899.
        When a cell is formatted as "Date" (not "Date time"), get_all_records()
        returns only the date portion (e.g. "15/01/2025").  By fetching with
        value_render_option='UNFORMATTED_VALUE' we get the raw float (e.g.
        45672.6128), which includes the time-of-day as the fractional part.
        This method converts that float back into "YYYY-MM-DD HH:MM:SS".

        # FIX: This is the core fix for the missing time issue.
        # Google Sheets stores datetime as a float (days since 30 Dec 1899).
        # The fractional part encodes the time. Using UNFORMATTED_VALUE gives
        # us this float so we can recover the full datetime including time.
        """
        try:
            serial = float(value)
        except (TypeError, ValueError):
            return str(value) if value else ""

        # Serials below 2 are sentinel/error values in Sheets
        if serial < 2:
            return str(value)

        # Google Sheets epoch: December 30, 1899
        epoch = datetime(1899, 12, 30)
        dt = epoch + timedelta(days=serial)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _parse_date_value(raw_value):
        """
        Accept either:
          - a float/int  → Google Sheets serial → convert to datetime string
          - a string     → return as-is (already a datetime or date string)
          - empty / None → return ""

        This handles both new records (stored as RAW text, come back as strings)
        and legacy records (stored as Sheets date values, come back as serials
        when fetched with UNFORMATTED_VALUE).

        # FIX: Handles both legacy float-serial rows AND new RAW string rows
        # so the date column always returns "YYYY-MM-DD HH:MM:SS" regardless
        # of how the value was originally written into the sheet.
        """
        if raw_value is None or raw_value == "":
            return ""

        if isinstance(raw_value, (int, float)):
            return GoogleSheetsHandler._serial_to_datetime_str(raw_value)

        value_str = str(raw_value).strip()

        # Already a full datetime string — return as-is
        if ":" in value_str and len(value_str) >= 16:
            return value_str

        # Date-only string like "2025-01-15" or "15/01/2025" — return as-is;
        # the frontend formatDateTime() will show "—" for the missing time part
        return value_str

    # ─── Accident record I/O ──────────────────────────────────────────────────

    def append_accident_record(self, record):
        """
        Append a new accident row to AccidentLogs sheet.
        Expects keys: date, Latitude, Longitude, Vibration, Distance

        # FIX: value_input_option="RAW" stores the datetime string exactly as
        # provided, preventing Google Sheets from converting it to a Date serial
        # (which would strip the time when the column format is "Date").
        # Without RAW, Sheets would parse "2025-01-15 14:32:07" as a date-only
        # serial and the time component would be lost on the next read.
        """
        try:
            row = [
                record.get("date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                record.get("Latitude", ""),
                record.get("Longitude", ""),
                record.get("Vibration", ""),
                record.get("Distance", "")
            ]
            # FIX: RAW — store the datetime string verbatim; Sheets will NOT
            # parse it as a date type, so the full "YYYY-MM-DD HH:MM:SS"
            # is always preserved and returned unchanged on the next read.
            self.sheet.append_row(row, value_input_option="RAW")
            return True
        except Exception as e:
            print(f"Error appending accident record: {e}")
            return False

    def get_accident_records(self):
        """
        Read all rows from AccidentLogs.
        Returns list of dicts with keys: date, latitude, longitude, vibration, distance.

        # FIX: Uses value_render_option='UNFORMATTED_VALUE' so that legacy cells
        # stored as Sheets date types come back as float serials (which we convert
        # to full datetime strings via _serial_to_datetime_str) instead of
        # display-formatted strings (which lose the time component when the
        # column is formatted as "Date" in Sheets).
        # New records written with value_input_option="RAW" come back as plain
        # strings and are returned unchanged by _parse_date_value.
        """
        try:
            # FIX: UNFORMATTED_VALUE is the key — dates return as float serials,
            # text returns as plain strings. This is what recovers the time part
            # for legacy rows that were stored as Sheets date values.
            raw_rows = self.sheet.get(value_render_option='UNFORMATTED_VALUE')

            if not raw_rows or len(raw_rows) < 2:
                return []

            headers = [str(h).strip() for h in raw_rows[0]]
            result = []

            for row in raw_rows[1:]:
                # Pad short rows so zip always produces a full dict
                padded = list(row) + [""] * (len(headers) - len(row))
                rec = dict(zip(headers, padded))

                # ── Date field ────────────────────────────────────────────────
                # FIX: _parse_date_value converts float serials → full datetime
                # string OR passes RAW strings through unchanged.
                raw_date = rec.get("date", rec.get("Date", ""))
                date_str = self._parse_date_value(raw_date)

                # ── Vibration field ───────────────────────────────────────────
                vib_raw = rec.get("Vibration", rec.get("vibration", "NO"))
                vib_str = str(vib_raw).strip().upper()
                if vib_str in ("YES", "1", "TRUE"):
                    vibration_display = "YES"
                elif vib_str in ("NO", "0", "FALSE", ""):
                    vibration_display = "NO"
                else:
                    vibration_display = vib_str

                # ── Distance field ────────────────────────────────────────────
                try:
                    distance = float(
                        rec.get("Distance", rec.get("distance", 0)) or 0
                    )
                except (ValueError, TypeError):
                    distance = 0.0

                result.append({
                    "date":      date_str,
                    "latitude":  str(rec.get("Latitude",  rec.get("latitude",  "")) or ""),
                    "longitude": str(rec.get("Longitude", rec.get("longitude", "")) or ""),
                    "vibration": vibration_display,
                    "distance":  distance,
                })

            return result

        except Exception as e:
            print(f"Error reading accident records: {e}")
            return []

    # ─── Parking helpers ──────────────────────────────────────────────────────

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
                distance  = record.get("Distance")  or record.get("Distance_cm") or record.get("distance")
                status    = record.get("Status")    or record.get("status") or ""

                if not timestamp or distance is None:
                    continue

                try:
                    distance_val = float(distance)
                except Exception:
                    distance_val = 0.0

                processed_data.append({
                    'timestamp':  timestamp,
                    'distance':   distance_val,
                    'status':     status,
                    'location':   record.get('Location') or record.get('location') or 'Unknown',
                    'device_id':  record.get('Device_ID') or record.get('DeviceId') or record.get('device') or None,
                    'rssi':       record.get('RSSI_dBm') or record.get('rssi') or None,
                    'latitude':   record.get('Latitude') or record.get('lat') or None,
                    'longitude':  record.get('Longitude') or record.get('lon') or None,
                    'raw':        record
                })

            return processed_data[-50:]

        except Exception as e:
            print(f"Error reading parking data from Google Sheets: {e}")
            return []

    def get_violations_since(self, since_time):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.sheet

            records    = sheet.get_all_records()
            violations = []

            for record in records:
                status    = record.get("Status")   or record.get("status") or ""
                distance  = record.get("Distance") or record.get("Distance_cm") or record.get("distance")
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
                            "location":  record.get("Location") or record.get("location") or "Unknown",
                            "distance":  distance_val,
                            "device_id": record.get("Device_ID") or record.get("device") or None,
                            "priority":  "HIGH" if distance_val < 5 else "MEDIUM"
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
            status_col   = "Status"   if "Status"   in df.columns else ("status"   if "status"   in df.columns else None)
            distance_col = "Distance" if "Distance" in df.columns else (
                "Distance_cm" if "Distance_cm" in df.columns else (
                    "distance" if "distance" in df.columns else None
                )
            )

            if status_col:
                available_spots = len(df[df[status_col] == "AVAILABLE"])
                occupied_spots  = len(df[df[status_col] == "OCCUPIED"])
            else:
                available_spots = occupied_spots = 0

            if status_col and distance_col:
                violation_count = len(
                    df[(df[status_col] == "OCCUPIED") & (df[distance_col].astype(float) < 10)]
                )
            else:
                violation_count = 0

            return {
                "total_records":    total_records,
                "available_spots":  available_spots,
                "occupied_spots":   occupied_spots,
                "violation_count":  violation_count,
                "utilization_rate": round((occupied_spots / total_records) * 100, 2) if total_records > 0 else 0
            }

        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}

    def get_device_health(self):
        return [
            {
                "device_id":   "SN-001",
                "location":    "Main Gate A1",
                "status":      "online",
                "battery":     85,
                "last_update": datetime.now().isoformat()
            },
            {
                "device_id":   "SN-002",
                "location":    "Street B2",
                "status":      "offline",
                "battery":     15,
                "last_update": (datetime.now() - timedelta(hours=3)).isoformat()
            }
        ]

    def append_parking_record(self, record):
        try:
            try:
                sheet = self.spreadsheet.worksheet("ParkingLogs")
            except Exception:
                sheet = self.spreadsheet.add_worksheet(title="ParkingLogs", rows="2000", cols="20")

            headers = [
                "Time", "Device_ID", "Location", "Distance_cm",
                "Vehicle_Detected", "Parking_Duration_s", "RSSI_dBm",
                "Latitude", "Longitude", "Status", "Received_At", "Raw_Params"
            ]

            values = sheet.get_all_values()
            if not values:
                sheet.insert_row(headers, index=1)

            row = [
                record.get("timestamp") or record.get("Time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                record.get("device")    or record.get("Device_ID")      or record.get("device_id")   or "",
                record.get("location")  or record.get("Location")       or "",
                record.get("distance")  or record.get("Distance")       or record.get("Distance_cm") or "",
                record.get("vehicle_detected") or record.get("Vehicle_Detected") or record.get("vehicle") or "",
                record.get("parking_duration") or record.get("Parking_Duration_s") or record.get("duration") or "",
                record.get("rssi")      or record.get("RSSI_dBm")      or "",
                record.get("lat")       or record.get("Latitude")       or "",
                record.get("lon")       or record.get("Longitude")      or "",
                record.get("Status")    or record.get("status")         or "",
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
                sheet = self.spreadsheet.add_worksheet(title="Actions", rows="1000", cols="10")

            headers = ["Time", "Device_ID", "Action", "Note", "User", "Recorded_At"]
            values  = sheet.get_all_values()
            if not values:
                sheet.insert_row(headers, index=1)

            row = [
                action.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                action.get("device_id") or action.get("device") or "",
                action.get("action")    or "",
                action.get("note")      or "",
                action.get("user")      or "",
                datetime.now().isoformat()
            ]

            sheet.append_row(row, value_input_option="USER_ENTERED")
            return True

        except Exception as e:
            print(f"Error appending action record: {e}")
            return False