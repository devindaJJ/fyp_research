import sys
import os
import json
import csv
import cv2
import threading
import time
import logging
import joblib
import traceback
import datetime
import queue
import pandas as pd

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from flask import Flask, jsonify, request
from flask_cors import CORS
from google_sheets import GoogleSheetsHandler
from traffic_routes import traffic_bp
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.integration import VehicleDataIntegrator
from src.utils.safety_detector import SafetyEventDetector
from src.utils.exporter import ResultExporter
from src.speed.detector import VehicleSpeedDetector
from src.anpr.detector import NumberPlateDetector

# Global variables to store current session data
current_session = {
    'integrator': None,
    'safety_detector': None,
    'speed_detector': None,
    'anpr_detector': None,
    'is_processing': False,
    'current_video': None,
    'frame_count': 0,
    'processing_thread': None
}
accident_records = []


app = Flask(__name__)
CORS(app)  

app.register_blueprint(traffic_bp)

try:
    sheets_handler = GoogleSheetsHandler()
except Exception as e:
    sheets_handler = None
    logging.error(f"Failed to initialize GoogleSheetsHandler: {e}")

PARKING_MEMORY_MAX = 500
parking_records_in_memory = []

# --- ML models, Google Sheets worksheet, and accident detector ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'src', 'models', 'trained')

logging.info(f"Looking for models in: {MODEL_PATH}")

model_distance = None
model_impact = None
model_alert = None

try:
    model_distance_path = os.path.join(MODEL_PATH, 'model_distance_violation.pkl')
    model_impact_path = os.path.join(MODEL_PATH, 'model_impact_detected.pkl')
    model_alert_path = os.path.join(MODEL_PATH, 'model_alert_level.pkl')
    
    logging.info(f"Checking files:")
    logging.info(f"  Distance model exists: {os.path.exists(model_distance_path)}")
    logging.info(f"  Impact model exists: {os.path.exists(model_impact_path)}")
    logging.info(f"  Alert model exists: {os.path.exists(model_alert_path)}")
    
    model_distance = joblib.load(model_distance_path)
    model_impact = joblib.load(model_impact_path)
    model_alert = joblib.load(model_alert_path)
    
    logging.info("ML Models loaded successfully")
except FileNotFoundError as e:
    logging.warning(f"Model files not found: {e}")
    model_distance = None
    model_impact = None
    model_alert = None
except Exception as e:
    logging.warning(f"Error loading ML models: {e}")
    model_distance = None
    model_impact = None
    model_alert = None

# Google Sheets worksheet used by ML detector
worksheet = None


def get_sheets_handler():
    global sheets_handler
    if sheets_handler is None:
        try:
            creds_default = os.getenv('SERVICE_ACCOUNT_CREDS') or str(Path(__file__).parent.parent / 'keys' / 'credentials.json')
            if not os.getenv('SERVICE_ACCOUNT_CREDS') and os.path.exists(creds_default):
                os.environ['SERVICE_ACCOUNT_CREDS'] = creds_default
                logging.info(f"SERVICE_ACCOUNT_CREDS was not set; using default: {creds_default}")

            sheets_handler = GoogleSheetsHandler()
        except Exception as e:
            logging.warning(f"GoogleSheetsHandler init failed: {e}")
            logging.debug(traceback.format_exc())
            return None
    return sheets_handler


def init_google_sheets():
    try:
        gh = None
        try:
            gh = get_sheets_handler()
        except Exception:
            gh = None
        if gh is not None:
            try:
                if hasattr(gh, 'sheet') and gh.sheet is not None:
                    try:
                        if getattr(gh.sheet, 'title', None) == 'AccidentLogs':
                            return gh.sheet
                    except Exception:
                        pass
                if hasattr(gh, 'client') and os.getenv('SHEET_ID'):
                    try:
                        return gh.client.open_by_key(os.getenv('SHEET_ID')).worksheet('AccidentLogs')
                    except Exception as e:
                        logging.warning(f"Could not open 'AccidentLogs' via GoogleSheetsHandler: {e}")
            except Exception as e:
                logging.warning(f"GoogleSheetsHandler usage error: {e}")
        creds_path = os.getenv('SERVICE_ACCOUNT_CREDS') or str(Path(__file__).parent.parent / 'keys' / 'credentials.json')
        logging.info(f"SERVICE_ACCOUNT_CREDS set: {bool(os.getenv('SERVICE_ACCOUNT_CREDS'))}, creds_path exists: {os.path.exists(creds_path)}")
        logging.info(f"SHEET_ID env present: {bool(os.getenv('SHEET_ID'))}")
        if os.path.exists(creds_path):
            try:
                scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
                from google.oauth2.service_account import Credentials
                creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
                client = gspread.authorize(creds)
                sheet_id = os.getenv('SHEET_ID')
                if sheet_id:
                    sheet = client.open_by_key(sheet_id)
                    worksheet = sheet.worksheet('AccidentLogs')
                    return worksheet
            except Exception as e:
                logging.warning(f"gspread fallback failed: {e}")
        return None
    except Exception as e:
        logging.warning(f"Google Sheets initialization error: {e}")
        return None


# ML / accident detector state
accidents = []
from collections import deque
vibration_data_history = deque(maxlen=1000)
accident_alerts = []
connected_devices = {}
ml_predictions = []

ACCIDENT_COOLDOWN = 60


def load_accidents_from_sheets(detector):
    global worksheet

    if worksheet is None:
        worksheet = init_google_sheets()

    if not worksheet:
        logging.warning("No worksheet found")
        return

    try:
        records = worksheet.get_all_records()
        logging.info(f"Loading {len(records)} records from Google Sheets...")

        for record in records:
            try:
                date = record.get("date", "")

                lat = record.get("Latitude") or record.get("latitude") or ""
                lon = record.get("Longitude") or record.get("longitude") or ""

                vibration_raw = record.get("Vibration", 0)

                if str(vibration_raw).upper() in ("YES", "NO"):
                    vibration_display = str(vibration_raw).upper()
                else:
                    vibration_display = str(vibration_raw)

                if str(vibration_raw).upper() == "YES":
                    vibration_numeric = 10
                else:
                    try:
                        vibration_numeric = float(vibration_raw)
                    except Exception:
                        vibration_numeric = 0

                distance = float(record.get("Distance", 0) or 0)

                detected = vibration_numeric > 5 or str(vibration_raw).upper() == "YES"

                accident_internal = {
                    "id": f"acc_{date}",
                    "date": date,
                    "latitude": lat,
                    "longitude": lon,
                    "vibration": vibration_numeric,
                    "distance": distance,
                    "detected": detected,
                    "severity": "high" if vibration_numeric > 8 else "medium" if vibration_numeric > 5 else "low",
                    "status": "historical"
                }
                detector.accident_log.append(accident_internal)

                accident_records.append({
                    "id": f"acc_{date}",
                    "date": date,
                    "latitude": lat,
                    "longitude": lon,
                    "vibration": vibration_display,
                    "distance": distance,
                    "detected": detected,
                    "severity": accident_internal["severity"],
                    "status": "historical"
                })

                device_id = record.get("Device_ID", "DEVICE_1")

                connected_devices[device_id] = {
                    "device_id": device_id,
                    "location": f"{lat}, {lon}",
                    "status": "online",
                    "last_seen": date,
                    "distance": distance,
                    "vibration": vibration_display
                }

            except Exception as e:
                logging.warning(f"Error parsing record: {e}")
                continue

        logging.info(f"Loaded {len(detector.accident_log)} accidents from Google Sheets into UI")

    except Exception as e:
        logging.warning(f"Error loading data from Google Sheets: {e}")


def read_accidents_from_sheets():
    global worksheet

    if worksheet is None:
        worksheet = init_google_sheets()

    if not worksheet:
        logging.warning("read_accidents_from_sheets: no worksheet available")
        return []

    try:
        records = worksheet.get_all_records()
        result = []

        for rec in records:
            try:
                date     = rec.get("date", "") or rec.get("Date", "")
                lat      = str(rec.get("Latitude",  rec.get("latitude",  "")) or "")
                lon      = str(rec.get("Longitude", rec.get("longitude", "")) or "")
                dist_raw = rec.get("Distance", rec.get("distance", 0)) or 0
                vib_raw  = rec.get("Vibration", rec.get("vibration", "NO"))

                vib_str = str(vib_raw).strip().upper()
                if vib_str in ("YES", "1", "TRUE"):
                    vibration_display = "YES"
                elif vib_str in ("NO", "0", "FALSE", ""):
                    vibration_display = "NO"
                else:
                    vibration_display = vib_str

                try:
                    distance = float(dist_raw)
                except (ValueError, TypeError):
                    distance = 0.0

                result.append({
                    "date":      date,
                    "latitude":  lat,
                    "longitude": lon,
                    "vibration": vibration_display,
                    "distance":  distance,
                })
            except Exception as row_err:
                logging.warning(f"Skipping bad row: {row_err}")
                continue

        return result

    except Exception as e:
        logging.warning(f"read_accidents_from_sheets error: {e}")
        worksheet = None
        return []


# ─────────────────────────────────────────────────────────────────────────────
# Email alert — persistent queue + worker thread (FIX: was daemon=True,
# one-shot thread that could be killed mid-send; now uses a queue so every
# alert is guaranteed to be attempted even under load)
# ─────────────────────────────────────────────────────────────────────────────

_email_queue: queue.Queue = queue.Queue()


def _email_worker():
    """
    Background worker that drains _email_queue and sends each alert.
    Runs as a non-daemon thread so it completes even if the main thread is busy.
    Retries up to 3 times with a short back-off before giving up.
    """
    while True:
        accident = _email_queue.get()          # blocks until an item arrives
        if accident is None:                   # sentinel → shut down
            break

        MAX_RETRIES = 3
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                _do_send_email(accident)
                break                          # success — no retry needed
            except Exception as e:
                logging.warning(
                    f"Email attempt {attempt}/{MAX_RETRIES} failed: {e}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(5 * attempt)    # 5 s, 10 s back-off

        _email_queue.task_done()


# Start the worker once at import time (non-daemon so sends always complete)
_email_worker_thread = threading.Thread(target=_email_worker, daemon=False)
_email_worker_thread.start()


def _do_send_email(accident: dict):
    """
    Core SMTP send.  Credentials come from environment variables first;
    the original hard-coded values are used as fallbacks so nothing breaks
    if the env vars are not set.
    """
    SENDER_EMAIL   = os.getenv("ALERT_SENDER_EMAIL",   "madhukaishani123@gmail.com")
    RECEIVER_EMAIL = os.getenv("ALERT_RECEIVER_EMAIL", "ishanimadhuka12345@gmail.com")
    APP_PASSWORD   = os.getenv("ALERT_EMAIL_PASSWORD", "ioxfxuuzzszwhabz")

    severity  = str(accident.get("severity",  "unknown")).upper()
    device_id = str(accident.get("device_id", "N/A"))
    latitude  = str(accident.get("latitude",  "N/A"))
    longitude = str(accident.get("longitude", "N/A"))
    timestamp = str(accident.get("timestamp", datetime.now().isoformat()))
    distance  = str(accident.get("distance",  "N/A"))
    vibration = accident.get("vibration", 0)

    print(f"\n{'='*50}")
    print(f"  Sending accident alert email...")
    print(f"  From    : {SENDER_EMAIL}")
    print(f"  To      : {RECEIVER_EMAIL}")
    print(f"  Severity: {severity}")
    print(f"{'='*50}\n")

    msg = EmailMessage()
    msg["Subject"] = f"ACCIDENT DETECTED - Severity: {severity}"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg.set_content(
        f"ACCIDENT ALERT\n"
        f"==============\n\n"
        f"Device ID  : {device_id}\n"
        f"Severity   : {severity}\n"
        f"Timestamp  : {timestamp}\n"
        f"Latitude   : {latitude}\n"
        f"Longitude  : {longitude}\n"
        f"Distance   : {distance} cm\n"
        f"Vibration  : {'YES' if vibration else 'NO'}\n\n"
        f"Maps Link  : https://maps.google.com/?q={latitude},{longitude}\n\n"
        f"Check the dashboard immediately.\n"
    )

    print("  [1/4] Connecting to smtp.gmail.com:587 ...")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
        print("  [2/4] Starting TLS ...")
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("  [3/4] Logging in ...")
        server.login(SENDER_EMAIL, APP_PASSWORD)
        print("  [4/4] Sending message ...")
        server.send_message(msg)

    print("\n  EMAIL SENT SUCCESSFULLY!\n")
    logging.info(f"Accident alert email sent to {RECEIVER_EMAIL}")


def send_accident_alert_email(accident: dict):
    """
    Public helper — enqueues the accident for the persistent worker thread.
    Returns immediately; actual sending happens in the background.
    """
    print(f"  [EMAIL QUEUE] Queuing alert for device {accident.get('device_id')} ...")
    _email_queue.put(accident)


class MLAccidentDetector:
    def __init__(self):
        self.accident_log = []
        self.device_last_accident = {}
        self.running = True

    def predict_with_ml(self, distance, vibration):
        if not all([model_distance, model_impact, model_alert]):
            return None

        try:
            # ✅ FIX 1: IoT sends vibration as 0 or 1, not 0-10.
            # Changed from `> 5` to `> 0` so vibration=1 is correctly treated as impact.
            impact_detected = 1 if int(vibration) > 0 else 0
            total_impacts = 1

            features = [[distance, impact_detected, total_impacts]]

            prediction = {
                "distance_violation": int(model_distance.predict(features)[0]),
                "impact_detected": int(model_impact.predict(features)[0]),
                "alert_level": int(model_alert.predict(features)[0]),
            }

            alert_levels = {
                0: "NORMAL",
                1: "LOW",
                2: "MEDIUM",
                3: "HIGH",
                4: "CRITICAL"
            }

            prediction["alert_level_text"] = alert_levels.get(
                prediction["alert_level"], "UNKNOWN"
            )

            return prediction

        except Exception as e:
            logging.warning(f"ML Prediction error: {e}")
            return None

    def analyze_sensor_data(self, record):
        """
        Analyze incoming IoT sensor data, detect accidents, create alerts,
        and automatically send an email when an accident is confirmed.
        """
        try:
            device_id = record.get('device_id')
            distance = float(record.get('distance', 0))
            vibration = int(record.get('impact_detected', 0))
            timestamp = record.get('timestamp', datetime.now().isoformat())

            location = record.get('location', '')

            latitude = record.get('latitude', '')
            longitude = record.get('longitude', '')

            if not latitude and not longitude and location and ',' in location:
                try:
                    lat_str, lon_str = location.split(',', 1)
                    latitude = lat_str.strip()
                    longitude = lon_str.strip()
                except ValueError:
                    latitude = ""
                    longitude = ""

            ml_pred = self.predict_with_ml(distance, vibration)

            if ml_pred:
                ml_predictions.append({
                    "device_id": device_id,
                    "timestamp": timestamp,
                    "input": {
                        "distance": distance,
                        "vibration": vibration
                    },
                    "prediction": ml_pred
                })

                if len(ml_predictions) > 500:
                    ml_predictions.pop(0)

            # ✅ FIX 2: Added fallback so if ML models are not loaded,
            # we still detect accidents using raw vibration and distance from IoT.
            # vibration == 1 means sensor detected impact.
            # distance < 10 means something is dangerously close.
            if ml_pred:
                is_accident = (
                    ml_pred["impact_detected"] == 1 or
                    ml_pred["alert_level"] >= 2
                )
            else:
                # Fallback: no ML models loaded — use raw sensor values directly
                is_accident = (vibration == 1) or (distance > 0 and distance < 10)
                print(f"  [ML FALLBACK] vibration={vibration}, distance={distance}, is_accident={is_accident}")

            if not is_accident:
                print(f"  [NO ACCIDENT] vibration={vibration}, distance={distance}, ml_pred={ml_pred}")
                return None

            if device_id in self.device_last_accident:
                last_time = self.device_last_accident[device_id]
                if (datetime.now() - last_time).total_seconds() < ACCIDENT_COOLDOWN:
                    print(f"  [COOLDOWN] Skipping accident for device {device_id} — cooldown active")
                    return None

            # Determine severity
            if ml_pred:
                severity_map = {
                    0: "low",
                    1: "low",
                    2: "medium",
                    3: "high",
                    4: "critical"
                }
                severity = severity_map.get(ml_pred["alert_level"], "medium")
            else:
                # Fallback severity based on raw distance
                if distance < 5:
                    severity = "critical"
                elif distance < 10:
                    severity = "high"
                else:
                    severity = "medium"

            accident = {
                "id": f"acc_{device_id}_{int(time.time())}",
                "device_id": device_id,
                "distance": distance,
                "vibration": vibration,
                "severity": severity,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": timestamp,
                "status": "detected",
                "confirmed": False,
                "ml_prediction": ml_pred
            }

            self.accident_log.append(accident)
            self.device_last_accident[device_id] = datetime.now()

            alert = {
                "id": f"alert_{device_id}_{int(time.time())}",
                "type": "accident",
                "title": f"Accident Detected - {severity.upper()}",
                "message": f"Location: {latitude}, {longitude} | Distance: {distance} cm | Vibration: {'YES' if vibration else 'NO'}",
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "read": False
            }

            accident_alerts.append(alert)

            if len(accident_alerts) > 100:
                accident_alerts.pop(0)

            print(f"  [ACCIDENT DETECTED] severity={severity}, device={device_id} — queuing email alert...")

            # ✅ FIX 3: enqueue instead of spawning a raw daemon thread.
            # The persistent _email_worker thread (non-daemon) guarantees
            # delivery even when the server is under load.
            send_accident_alert_email(accident)

            return accident

        except Exception as e:
            logging.warning(f"Analyze error: {e}")
            logging.debug(traceback.format_exc())
            return None

        
# Instantiate detector
detector = MLAccidentDetector()


try:
    sheets_handler = get_sheets_handler()
    load_accidents_from_sheets(detector)
except Exception:
    logging.info("No historical accidents loaded or load failed")

def process_video_in_background():
    """Process video in background thread"""
    try:
        video_path = current_session['current_video']
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video file: {video_path}")
            current_session['is_processing'] = False
            return
        
        speed_detector = current_session['speed_detector']
        anpr_detector = current_session['anpr_detector']
        integrator = current_session['integrator']
        safety_detector = current_session['safety_detector']
        
        print(f"[INFO] Starting video processing: {video_path}")
        frame_count = 0
        
        while current_session['is_processing'] and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print(f"[INFO] Video ended. Processed {frame_count} frames")
                current_session['is_processing'] = False
                break
            
            frame_count += 1
            current_session['frame_count'] = frame_count
            
            try:
                detections = speed_detector.detect_vehicles(frame)
                tracks = speed_detector.tracker.update_tracks(detections, frame=frame)
                active_ids = speed_detector.process_tracks(tracks, frame)
                
                plates_data = anpr_detector.detect_and_read(frame, draw_results=False)
                if isinstance(plates_data, tuple):
                    plates_data = plates_data[0]
                
                current_tracks = speed_detector.get_current_tracks()
                
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        bbox = track_data.get('bbox')
                        speed = track_data.get('speed')
                        if bbox:
                            integrator.update_vehicle_tracking(track_id, bbox, speed)
                
                if plates_data and isinstance(plates_data, list):
                    integrator.link_plates_to_vehicles(plates_data)
                
                # Safety detection
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        speed = track_data.get('speed')
                        bbox = track_data.get('bbox')
                        
                        if speed is not None and bbox is not None:
                            safety_detector.update_vehicle_state(track_id, bbox, speed)
                    
                alerts = safety_detector.process_frame(current_tracks)
                print(f"[INFO] Processed {frame_count} frames, {len(integrator.get_violations())} violations")
                
                if frame_count % 2 == 0:
                    continue
                    
            except Exception as frame_error:
                print(f"[ERROR] Frame {frame_count} processing failed: {frame_error}")
                traceback.print_exc()
                continue
            if current_session['frame_count'] % 3 != 0:
                continue
                
        cap.release()
        print(f"[INFO] Processed {current_session['frame_count']} frames")
        
    except Exception as e:
        print(f"[ERROR] Video processing failed: {e}")
        current_session['is_processing'] = False

@app.route('/')
def home():
    return jsonify({"message": "Traffic Management API is running!"})

@app.route('/api/detection/status', methods=['GET'])
def get_detection_status():
    """Get current detection session status"""
    return jsonify({
        "success": True,
        "is_processing": current_session['is_processing'],
        "current_video": current_session['current_video'],
        "frame_count": current_session['frame_count']
    })


@app.route('/api/detection/vehicles', methods=['GET'])
def get_vehicles():
    """Get all tracked vehicles and their data"""
    if not current_session['integrator']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        vehicles = current_session['integrator'].get_all_vehicles()
        
        vehicle_list = []
        for track_id, data in vehicles.items():
            vehicle_list.append({
                'track_id': track_id,
                'speed': data.get('speed'),
                'plate': data.get('plate'),
                'violation': data.get('violation'),
                'bbox': data.get('bbox')
            })
        
        return jsonify({
            "success": True,
            "vehicles": vehicle_list,
            "total_count": len(vehicle_list),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error in get_accidents: {e}")
        logging.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/ingest-parking', methods=['POST'])
def ingest_parking():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        records = payload if isinstance(payload, list) else [payload]
        appended = 0
        for rec in records:
            rec = rec or {}
            if not rec.get('timestamp') and not rec.get('Time'):
                rec['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'Status' not in rec and 'status' not in rec:
                dist = rec.get('distance') or rec.get('Distance') or rec.get('Distance_cm') or 9999
                try:
                    dval = float(dist)
                except Exception:
                    dval = 9999
                rec['Status'] = 'OCCUPIED' if dval < 200 else 'VACANT'

            parking_records_in_memory.append(rec)
            if len(parking_records_in_memory) > PARKING_MEMORY_MAX:
                parking_records_in_memory.pop(0)
            if sheets_handler:
                sheets_handler.append_parking_record(rec)
            appended += 1

        return jsonify({"success": True, "appended": appended}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ===== PARKING UPDATE ENDPOINT FOR ESP32 SENSORS =====
# Receives parking data directly from ultrasonic sensors (HC-SR04)
# Maps ESP32 format to backend parking schema
@app.route('/api/parking/update', methods=['POST'])
def parking_update():
    """
    Endpoint for ESP32 parking sensors to POST real-time parking data.
    
    Expected ESP32 JSON format:
    {
        "slot_id": "SLOT_001",
        "zone": "Zone_A",
        "status": "OCCUPIED" or "AVAILABLE",
        "distance_cm": 45.5,
        "latitude": 7.208430,
        "longitude": 79.864670
    }
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400
        
        # Map ESP32 format to backend parking format
        record = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Device_ID': payload.get('slot_id', 'UNKNOWN'),
            'Location': payload.get('location', f"{payload.get('zone', 'Zone_Unknown')}_{payload.get('slot_id', 'UNKNOWN')}"),
            'Distance_cm': payload.get('distance_cm', ''),
            'Vehicle_Detected': 'YES' if payload.get('status', '').upper() == 'OCCUPIED' else 'NO',
            'Status': payload.get('status', '').upper() or 'VACANT',
            'Latitude': payload.get('latitude', ''),
            'Longitude': payload.get('longitude', ''),
            'Zone': payload.get('zone', ''),
            'RSSI_dBm': payload.get('rssi', ''),
            'parking_duration': payload.get('parking_duration', ''),
            'slot_id': payload.get('slot_id', '')
        }
        
        # Store in Google Sheets
        if sheets_handler:
            sheets_handler.append_parking_record(record)
            logging.info(f"✓ Parking data received from {record['Device_ID']}: {record['Status']} at distance {record['Distance_cm']}cm")
            return jsonify({
                "success": True,
                "message": "Parking data received",
                "slot_id": payload.get('slot_id'),
                "status": record['Status'],
                "timestamp": record['timestamp']
            }), 201
        else:
            return jsonify({"success": False, "error": "Google Sheets handler not available"}), 500
            
    except Exception as e:
        logging.error(f"✗ Error in parking_update: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/detection/violations', methods=['GET'])
def get_detection_violations():
    """Get vehicles with violations"""
    if not current_session['integrator']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        violations = current_session['integrator'].get_violations()
        
        violation_list = []
        for vehicle in violations:
            violation_list.append({
                'track_id': vehicle['track_id'],
                'speed': vehicle['speed'],
                'plate': vehicle['plate'],
                'speed_limit': 60
            })
        
        return jsonify({
            "success": True,
            "violations": violation_list,
            "total_count": len(violation_list)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Receive live sensor data from IoT device.
    Stores vibration as YES/NO string matching Google Sheets format.
    """
    try:
        data = request.get_json()

        print("RECEIVED:", data)

        device_id = data.get('device_id')
        distance = float(data.get('distance', 0))
        location = data.get('location', '')
        vibration = int(data.get('impact_detected', 0))
        timestamp = data.get('timestamp', datetime.now().isoformat())

        latitude = data.get('latitude', '')
        longitude = data.get('longitude', '')
        
        print(f"Initial - latitude: '{latitude}', longitude: '{longitude}', location: '{location}'")
        
        if (not latitude and not longitude) and location and ',' in location:
            try:
                parts = location.split(',', 1)
                if len(parts) == 2:
                    latitude = parts[0].strip()
                    longitude = parts[1].strip()
                    print(f"Parsed location - latitude: '{latitude}', longitude: '{longitude}'")
            except Exception as e:
                print(f"Error parsing location: {e}")
                latitude = ''
                longitude = ''

        vibration_display = "YES" if vibration == 1 else "NO"

        record = {
            "date": timestamp,
            "Latitude": latitude,
            "Longitude": longitude,
            "Vibration": vibration_display,
            "Distance": distance
        }

        accident_records.append({
            "date": timestamp,
            "latitude": latitude,
            "longitude": longitude,
            "vibration": vibration_display,
            "distance": distance
        })

        print("SAVED RECORD:", record)
        print("TOTAL:", len(accident_records))

        if sheets_handler:
            sheets_handler.append_accident_record(record)

        # Run ML accident analysis (email is queued inside if accident detected)
        detector.analyze_sensor_data({
            "device_id": device_id,
            "distance": distance,
            "impact_detected": vibration,
            "timestamp": timestamp,
            "location": location,
            "latitude": latitude,
            "longitude": longitude,
        })

        return jsonify({
            "success": True,
            "record": record,
            "total": len(accident_records)
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/accidents', methods=['GET'])
def get_accidents():
    """Get all accident records — re-read from Google Sheets on every call."""
    try:
        live_records = read_accidents_from_sheets()

        return jsonify({
            "success": True,
            "accidents": live_records,
            "total_count": len(live_records),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logging.error(f"Error in get_accidents: {e}")
        logging.error(traceback.format_exc())

        return jsonify({
            "success": False,
            "error": str(e),
            "accidents": []
        }), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get alerts"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        filtered_alerts = accident_alerts
        if unread_only:
            filtered_alerts = [a for a in accident_alerts if not a['read']]
        return jsonify({
            "success": True,
            "alerts": filtered_alerts,
            "unread_count": len([a for a in accident_alerts if not a['read']])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/ml-predictions', methods=['GET'])
def get_ml_predictions():
    """Get recent ML predictions"""
    try:
        limit = request.args.get('limit', type=int, default=50)
        return jsonify({"success": True, "predictions": ml_predictions[-limit:], "count": len(ml_predictions)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    try:
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        recent_accidents = []
        for a in detector.accident_log:
            try:
                timestamp_str = a.get('date') or a.get('timestamp', '')
                if not timestamp_str:
                    continue
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except Exception:
                    try:
                        ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        continue
                if ts > last_24h:
                    recent_accidents.append(a)
            except Exception as e:
                logging.warning(f"Error processing accident in statistics: {e}")
                continue

        stats = {
            "total_accidents": len(detector.accident_log),
            "accidents_last_24h": len(recent_accidents),
            "active_alerts": len([a for a in accident_alerts if not a['read']]),
            "connected_devices": len(connected_devices),
            "ml_models_active": all([model_distance, model_impact, model_alert]),
            "total_predictions": len(ml_predictions)
        }

        return jsonify({"success": True, "statistics": stats, "timestamp": now.isoformat()})
    except Exception as e:
        logging.error(f"Error in get_statistics: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get connected devices"""
    try:
        return jsonify({"success": True, "devices": list(connected_devices.values()), "total_online": len(connected_devices)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/detection/safety-alerts', methods=['GET'])
def get_safety_alerts():
    """Get safety alerts from current session"""
    if not current_session['safety_detector']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        alerts = current_session['safety_detector'].alerts
        
        alert_list = []
        for alert in alerts[-100:]:
            alert_list.append({
                'type': alert['type'],
                'severity': alert['severity'],
                'track_ids': alert.get('track_ids', [alert.get('track_id', 'N/A')]),
                'description': alert['description'],
                'timestamp': alert['timestamp'].isoformat()
            })
        
        return jsonify({
            "success": True,
            "alerts": alert_list,
            "total_count": len(alerts),
            "critical_count": len(current_session['safety_detector'].collisions)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# --- Lane Violation Detection Endpoints ---

@app.route('/api/violations/lane', methods=['GET'])
def get_lane_violations():
    """Get all detected lane violations"""
    if not current_session['integrator']:
        # Return sample data for development/testing when no active session
        sample_violations = [
            {
                'type': 'ILLEGAL_LANE_CHANGE',
                'track_id': 1,
                'severity': 'medium',
                'description': 'Vehicle changed lanes without signaling',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'LANE_CROSSING',
                'track_id': 2,
                'severity': 'high',
                'description': 'Vehicle crossed multiple lane markings',
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'EXCESSIVE_LANE_CHANGES',
                'track_id': 3,
                'severity': 'low',
                'description': 'Multiple lane changes in short time period',
                'timestamp': datetime.now().isoformat()
            }
        ]
        return jsonify({
            "success": True,
            "violations": sample_violations,
            "total_count": len(sample_violations),
            "note": "Sample data - no active detection session"
        })
    
    try:
        violations = current_session['integrator'].get_lane_violations()
        
        violation_list = []
        for v in violations:
            violation_list.append({
                'type': v.get('type'),
                'track_id': v.get('track_id'),
                'severity': v.get('severity'),
                'description': v.get('description'),
                'timestamp': v.get('timestamp').isoformat() if hasattr(v.get('timestamp'), 'isoformat') else str(v.get('timestamp'))
            })
        
        return jsonify({
            "success": True,
            "violations": violation_list,
            "total_count": len(violation_list)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/violations/summary', methods=['GET'])
def get_violation_summary():
    """Get summary of all violations (speed and lane)"""
    if not current_session['integrator']:
        # Return sample data for development/testing when no active session
        return jsonify({
            "success": True,
            "summary": {
                "total_violations": 8,
                "speed_violations": 2,
                "lane_violations": 6,
                "vehicles_with_violations": 5
            },
            "violation_breakdown": {
                "speed": [
                    {"type": "SPEEDING", "count": 2}
                ],
                "lane": [
                    {"type": "ILLEGAL_LANE_CHANGE", "count": 3},
                    {"type": "LANE_CROSSING", "count": 2},
                    {"type": "EXCESSIVE_LANE_CHANGES", "count": 1}
                ]
            },
            "note": "Sample data - no active detection session"
        })
    
    try:
        integrator = current_session['integrator']
        speed_viols = integrator.get_speed_violations()
        lane_viols = integrator.get_lane_violations()
        all_viols = integrator.get_all_violations()
        
        # Get violation types for speed violations
        speed_types = {}
        for v in speed_viols:
            vtype = v.get('type', 'UNKNOWN')
            speed_types[vtype] = speed_types.get(vtype, 0) + 1
        
        # Get violation types for lane violations
        lane_types = {}
        for v in lane_viols:
            vtype = v.get('type', 'UNKNOWN')
            lane_types[vtype] = lane_types.get(vtype, 0) + 1
        
        return jsonify({
            "success": True,
            "summary": {
                "total_violations": len(all_viols),
                "speed_violations": len(speed_viols),
                "lane_violations": len(lane_viols),
                "vehicles_with_violations": len(integrator.get_violations())
            },
            "violation_breakdown": {
                "speed": [
                    {"type": vtype, "count": count}
                    for vtype, count in speed_types.items()
                ],
                "lane": [
                    {"type": vtype, "count": count}
                    for vtype, count in lane_types.items()
                ]
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/violations/vehicle/<int:track_id>', methods=['GET'])
def get_vehicle_violations(track_id):
    """Get violations for a specific vehicle (track_id)"""
    if not current_session['integrator']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        integrator = current_session['integrator']
        vehicle = integrator.get_vehicle_data(track_id)
        
        if not vehicle:
            return jsonify({
                "success": False,
                "error": f"Vehicle with track_id {track_id} not found"
            }), 404
        
        lane_violations = vehicle.get('lane_violations', [])
        
        return jsonify({
            "success": True,
            "vehicle": {
                'track_id': vehicle.get('track_id'),
                'plate': vehicle.get('plate'),
                'speed': vehicle.get('speed'),
                'speed_violation': vehicle.get('speed_violation'),
                'total_violations': vehicle.get('total_violations'),
                'lane_violations': [
                    {
                        'type': v.get('type'),
                        'severity': v.get('severity'),
                        'description': v.get('description'),
                        'timestamp': v.get('timestamp').isoformat() if hasattr(v.get('timestamp'), 'isoformat') else str(v.get('timestamp'))
                    }
                    for v in lane_violations
                ]
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/detection/start', methods=['POST'])
def start_detection():
    """Start a new detection session"""
    try:
        data = request.json
        video_path = data.get('video_path')
        
        if not video_path:
            return jsonify({
                "success": False,
                "error": "No video path provided"
            }), 400
        
        if not os.path.isabs(video_path):
            project_root = Path(__file__).parent.parent
            video_path = str(project_root / video_path)
            print(f"[INFO] Converted to absolute path: {video_path}")
            
        if not os.path.exists(video_path):
            return jsonify({
                "success": False,
                "error": f"Video file not found: {video_path}"
            }), 400
        
        test_cap = cv2.VideoCapture(video_path)
        if not test_cap.isOpened():
            test_cap.release()
            return jsonify({
                "success": False,
                "error": f"Cannot open video file. Check if the file is a valid video format: {video_path}"
            }), 400
        test_cap.release()
        
        if current_session['is_processing']:
            current_session['is_processing'] = False
            if current_session['processing_thread']:
                current_session['processing_thread'].join(timeout=2)
        
        print(f"[INFO] Initializing detection session for: {video_path}")
        
        try:
            print("[INFO] Creating VehicleDataIntegrator...")
            current_session['integrator'] = VehicleDataIntegrator(speed_limit=60)
            
            print("[INFO] Creating SafetyEventDetector with lane detection...")
            current_session['safety_detector'] = SafetyEventDetector(enable_lane_detection=True)
            
            print(f"[INFO] Creating VehicleSpeedDetector with video: {video_path}")
            current_session['speed_detector'] = VehicleSpeedDetector(headless=True)
            
            print("[INFO] Creating NumberPlateDetector...")
            anpr_model_path = str(Path(__file__).parent.parent / "models" / "number_plate_yolo.pt")
            current_session['anpr_detector'] = NumberPlateDetector(
                model_path=anpr_model_path,
                languages=["en"],
                confidence_threshold=0.25,
                image_size=640
            )
            
            print("[INFO] All detectors initialized successfully")
            
        except Exception as init_error:
            print(f"[ERROR] Detector initialization failed: {init_error}")
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"Failed to initialize detectors: {str(init_error)}"
            }), 500
        
        current_session['is_processing'] = True
        current_session['current_video'] = video_path
        current_session['frame_count'] = 0
        
        thread = threading.Thread(target=process_video_in_background, daemon=True)
        thread.start()
        current_session['processing_thread'] = thread
        
        print(f"[INFO] Detection started for: {video_path}")
        
        return jsonify({
            "success": True,
            "message": "Detection session started",
            "video": video_path
        })
    except Exception as e:
        print(f"[ERROR] Start detection failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/detection/stop', methods=['POST'])
def stop_detection():
    """Stop current detection session"""
    try:
        current_session['is_processing'] = False
        
        if current_session['processing_thread']:
            current_session['processing_thread'].join(timeout=3)
        
        print("[INFO] Detection stopped")
        
        return jsonify({
            "success": True,
            "message": "Detection session stopped",
            "frames_processed": current_session['frame_count']
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/detection/stats', methods=['GET'])
def get_detection_stats():
    """Get comprehensive statistics"""
    if not current_session['integrator']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        vehicles = current_session['integrator'].get_all_vehicles()
        violations = current_session['integrator'].get_violations()
        safety_detector = current_session['safety_detector']
        integrator = current_session['integrator']
        
        stats = {
            'total_vehicles_tracked': len(vehicles),
            'vehicles_with_speed': sum(1 for v in vehicles.values() if v['speed'] is not None),
            'vehicles_with_plate': sum(1 for v in vehicles.values() if v['plate'] is not None),
            'speeding_violations': len(integrator.get_speed_violations()),
            'lane_violations': len(integrator.get_lane_violations()),
            'total_violations': len(integrator.get_all_violations()),
            'safety_alerts': {
                'total': len(safety_detector.alerts),
                'collisions': len(safety_detector.collisions),
                'near_misses': len(safety_detector.near_misses),
                'behavioral': len(safety_detector.behavioral_alerts)
            },
            'frame_count': current_session['frame_count']
        }
        
        return jsonify({
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/detection/export', methods=['POST'])
def export_detection_data():
    """Export detection results"""
    if not current_session['integrator']:
        return jsonify({
            "success": False,
            "error": "No active detection session"
        }), 400
    
    try:
        data = request.json
        export_format = data.get('format', 'csv')
        
        vehicles = current_session['integrator'].get_all_vehicles()
        exporter = ResultExporter()
        
        if export_format == 'csv':
            path = exporter.export_to_csv(vehicles)
        elif export_format == 'json':
            path = exporter.export_to_json(vehicles)
        elif export_format == 'violations':
            path = exporter.export_violations_only(vehicles)
        else:
            return jsonify({
                "success": False,
                "error": "Invalid format"
            }), 400
        
        return jsonify({
            "success": True,
            "export_path": path,
            "format": export_format
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/violations/history', methods=['GET'])
def get_violation_history():
    """Get historical violations from Google Sheets"""
    try:
        since_time = datetime.now() - timedelta(days=1)
        violations = sheets_handler.get_violations_since(since_time)
        
        return jsonify({
            "success": True,
            "violations": violations,
            "total_count": len(violations),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "violations": []
        }), 200


def _get_parking_data():
    if parking_records_in_memory:
        return parking_records_in_memory
    if sheets_handler:
        try:
            return sheets_handler.get_parking_data()
        except Exception:
            pass
    return []

@app.route('/api/parking/status', methods=['GET'])
def get_parking_status():
    """Get current parking status from Google Sheets"""
    try:
        parking_data = sheets_handler.get_parking_data()
        return jsonify({
            "success": True,
            "parking_data": parking_data,
            "total_spots": len(parking_data),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "parking_data": []
        }), 200

@app.route('/api/parking-data', methods=['GET'])
def get_parking_data():
    try:
        data = sheets_handler.get_parking_data()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/system/overview', methods=['GET'])
def get_system_overview():
    """Get complete system overview"""
    try:
        parking_data = _get_parking_data()
        occupied = sum(1 for p in parking_data if (p.get('status') or p.get('Status') or '').upper() == 'OCCUPIED')
        
        detection_active = current_session.get('is_processing', False)
        
        since_time = datetime.now() - timedelta(hours=1)
        recent_violations = sheets_handler.get_violations_since(since_time)
        
        overview = {
            'parking': {
                'total_spots': len(parking_data),
                'occupied_spots': occupied,
                'available_spots': len(parking_data) - occupied,
                'occupancy_rate': (occupied / len(parking_data) * 100) if parking_data else 0
            },
            'detection': {
                'is_active': detection_active,
                'current_video': current_session.get('current_video'),
                'tracked_vehicles': len(current_session['integrator'].get_all_vehicles()) if current_session['integrator'] else 0
            },
            'violations': {
                'last_hour': len(recent_violations),
                'recent': recent_violations[:5]
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "overview": overview
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/mark-action', methods=['POST'])
def mark_action():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        actions = payload if isinstance(payload, list) else [payload]
        appended = 0
        for act in actions:
            ok = sheets_handler.append_action(act)
            if ok:
                appended += 1

        return jsonify({"success": True, "appended": appended}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    logging.info("Starting Traffic Management + ML Accident Detection API...")
    logging.info(f"ML Models loaded: {all([model_distance, model_impact, model_alert])}")
    logging.info(f"Google Sheets connected: {worksheet is not None}")
    
    # Print all registered routes
    print("\n" + "="*60)
    print("REGISTERED ENDPOINTS:")
    print("="*60)
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"{rule.rule:50} [{methods}]")
    print("="*60 + "\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=8000, threaded=True, use_reloader=False)
    except Exception as e:
        logging.error(f"Failed to start Flask app: {e}")
        import traceback
        traceback.print_exc()

@app.route('/api/sheets/test', methods=['GET'])
def test_sheets():
    try:
        if sheets_handler is None:
            return jsonify({
                "success": False,
                "message": "Sheets handler is None"
            })

        return jsonify({
            "success": True,
            "message": "Sheets connected",
            "sheet_name": sheets_handler.sheet.title
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
        
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({
        "success": True,
        "message": "Backend is working"
    })