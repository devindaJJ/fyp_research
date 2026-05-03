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
import smtplib
from email.message import EmailMessage
import logging
import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials


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

# --- ML models, Google Sheets worksheet, and accident detector (merged from Ishani branch) ---
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

# Google Sheets worksheet used by ML detector (Ishani branch used gspread directly)
worksheet = None

def init_google_sheets():
    try:
        # Prefer project GoogleSheetsHandler if available
        gh = None
        try:
            gh = get_sheets_handler()
        except Exception:
            gh = None
        if gh is not None:
            try:
                # If the project handler exposes a worksheet-like object on `sheet`, use it
                if hasattr(gh, 'sheet') and gh.sheet is not None:
                    # If the existing sheet is the desired sheet, return it
                    try:
                        if getattr(gh.sheet, 'title', None) == 'AccidentLogs':
                            return gh.sheet
                    except Exception:
                        pass
                    # Otherwise attempt to open the named worksheet via the handler's client
                if hasattr(gh, 'client') and os.getenv('SHEET_ID'):
                    try:
                        return gh.client.open_by_key(os.getenv('SHEET_ID')).worksheet('AccidentLogs')
                    except Exception as e:
                        logging.warning(f"Could not open 'AccidentLogs' via GoogleSheetsHandler: {e}")
            except Exception as e:
                logging.warning(f"GoogleSheetsHandler usage error: {e}")
        # Fallback: try to use gspread with credentials file path from keys/credentials.json
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
alerts = []
connected_devices = {}
ml_predictions = []

ACCIDENT_COOLDOWN = 60


def load_accidents_from_sheets(detector):
    """Load existing accidents from Google Sheets on startup (best-effort)."""
    global worksheet
    if worksheet is None:
        worksheet = init_google_sheets()
    if not worksheet:
        return
    try:
        records = worksheet.get_all_records()
        logging.info(f"Loading {len(records)} records from Google Sheets...")
        for record in records:
            try:
                # Support multiple possible column names from different sheet versions
                def fld(rec, keys, default=None):
                    for k in keys:
                        if k in rec and rec[k] not in (None, ''):
                            return rec[k]
                    return default

                timestamp = fld(record, ['Timestamp', 'Time', 'Date'], '')
                device_id = fld(record, ['Device ID', 'DeviceID', 'Device'], 'UNKNOWN')
                distance = int(fld(record, ['Distance (cm)', 'Distance'], 0) or 0)
                impact_detected = 1 if str(fld(record, ['Impact Detected', 'Impact', 'Impacts'], 'NO')).upper() == 'YES' else 0
                total_impacts = int(fld(record, ['Total Impacts', 'Total Impacts', 'Impacts'], 0) or 0)
                location = fld(record, ['Status', 'Location', 'Place'], 'Unknown Location')
                alert_level_text = fld(record, ['Alert Level', 'Alert_Level', 'Level'], 'NORMAL')
                alert_level_map = {'NORMAL': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
                alert_level = alert_level_map.get(alert_level_text, 1)
                severity_map = {0: 'low', 1: 'low', 2: 'medium', 3: 'high', 4: 'critical'}
                severity = severity_map.get(alert_level, 'medium')
                accident = {
                    'id': f"acc_{device_id}_{timestamp}",
                    'device_id': device_id,
                    'distance': distance,
                    'impact_detected': impact_detected,
                    'total_impacts': total_impacts,
                    'severity': severity,
                    'location': location,
                    'timestamp': timestamp,
                    'status': 'historical',
                    'confirmed': True,
                    'ml_prediction': {
                        'alert_level': alert_level,
                        'alert_level_text': alert_level_text,
                        'distance_violation': 1 if record.get('Distance Violation', 'NO') == 'YES' else 0,
                        'impact_detected': impact_detected
                    }
                }
                detector.accident_log.append(accident)
                if device_id not in connected_devices:
                    connected_devices[device_id] = {
                        'device_id': device_id,
                        'location': location,
                        'status': 'online',
                        'last_seen': timestamp,
                        'distance': distance,
                        'impact_detected': impact_detected,
                        'total_impacts': total_impacts
                    }
            except Exception as e:
                logging.warning(f"Error parsing record: {e}")
                continue
        logging.info(f"Loaded {len(detector.accident_log)} accidents from Google Sheets")
    except Exception as e:
        logging.warning(f"Error loading data from Google Sheets: {e}")


class MLAccidentDetector:
    def __init__(self):
        self.accident_log = []
        self.device_last_accident = {}
        self.running = True

    def predict_with_ml(self, distance, impact_detected, total_impacts):
        if not all([model_distance, model_impact, model_alert]):
            return None
        try:
            features = [[distance, impact_detected, total_impacts]]
            prediction = {
                'distance_violation': int(model_distance.predict(features)[0]),
                'impact_detected': int(model_impact.predict(features)[0]),
                'alert_level': int(model_alert.predict(features)[0])
            }
            alert_levels = {0: 'NORMAL', 1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL'}
            prediction['alert_level_text'] = alert_levels.get(prediction['alert_level'], 'UNKNOWN')
            return prediction
        except Exception as e:
            logging.warning(f"ML Prediction error: {e}")
            return None

    def analyze_sensor_data(self, device_id, distance, impact_detected, total_impacts, location, timestamp):
        ml_pred = self.predict_with_ml(distance, impact_detected, total_impacts)
        if ml_pred:
            ml_predictions.append({
                'device_id': device_id,
                'timestamp': timestamp,
                'input': {'distance': distance, 'impact': impact_detected, 'total_impacts': total_impacts},
                'prediction': ml_pred
            })
            if len(ml_predictions) > 500:
                ml_predictions.pop(0)
        is_accident = ml_pred and (ml_pred['impact_detected'] == 1 or ml_pred['alert_level'] >= 2)
        if not is_accident:
            return None
        if device_id in self.device_last_accident:
            last_time = self.device_last_accident[device_id]
            time_diff = (datetime.now() - last_time).total_seconds()
            if time_diff < ACCIDENT_COOLDOWN:
                return None
        severity_map = {0: 'low', 1: 'low', 2: 'medium', 3: 'high', 4: 'critical'}
        severity = severity_map.get(ml_pred['alert_level'], 'medium')
        accident = {
            'id': f"acc_{device_id}_{int(time.time())}",
            'device_id': device_id,
            'distance': distance,
            'impact_detected': impact_detected,
            'total_impacts': total_impacts,
            'severity': severity,
            'location': location,
            'timestamp': timestamp,
            'status': 'detected',
            'confirmed': False,
            'ml_prediction': ml_pred
        }
        self.accident_log.append(accident)
        self.device_last_accident[device_id] = datetime.now()
        alert = {
            'id': f"alert_{device_id}_{int(time.time())}",
            'type': 'accident',
            'title': f"🚨 Accident Detected - {severity.upper()}",
            'message': f"ML Model detected accident at {location}. Distance: {distance}cm, Impact: {impact_detected}, Total Impacts: {total_impacts}",
            'severity': severity,
            'device_id': device_id,
            'location': location,
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'accident_id': accident['id']
        }
        alerts.append(alert)
        if len(alerts) > 100:
            alerts.pop(0)
        if worksheet:
            try:
                row = [
                    timestamp,
                    device_id,
                    distance,
                    'YES' if impact_detected else 'NO',
                    'YES' if ml_pred['distance_violation'] else 'NO',
                    total_impacts,
                    0,
                    timestamp,
                    0,
                    0,
                    'Active',
                    ml_pred['alert_level_text']
                ]
                worksheet.append_row(row)
            except Exception as e:
                logging.warning(f"Error logging to Google Sheets: {e}")
        return accident


# Instantiate detector (historical load will run after sheets handler is available)
detector = MLAccidentDetector()


def get_sheets_handler():
    global sheets_handler
    if sheets_handler is None:
        try:
            # Ensure SERVICE_ACCOUNT_CREDS env is set to a sensible default if a local creds file exists
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

# After sheets handler is available, attempt to load historical records into detector
try:
    # Initialize sheets_handler variable so endpoints can use it
    sheets_handler = get_sheets_handler()
    load_accidents_from_sheets(detector)
except Exception:
    logging.info("No historical accidents loaded or load failed")

def process_video_in_background():
    """Process video in background thread"""
    try:
        video_path = current_session['current_video']
        
        # Open video file
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
                # Detect vehicles (like main.py does)
                detections = speed_detector.detect_vehicles(frame)
                tracks = speed_detector.tracker.update_tracks(detections, frame=frame)
                active_ids = speed_detector.process_tracks(tracks, frame)
                
                # Run ANPR detection
                plates_data = anpr_detector.detect_and_read(frame, draw_results=False)
                if isinstance(plates_data, tuple):
                    plates_data = plates_data[0]
                
                # Get current tracks
                current_tracks = speed_detector.get_current_tracks()
                
                # Update integrator with tracking data
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        bbox = track_data.get('bbox')
                        speed = track_data.get('speed')
                        if bbox:
                            integrator.update_vehicle_tracking(track_id, bbox, speed)
                
                # Link plates to vehicles
                if plates_data and isinstance(plates_data, list):
                    integrator.link_plates_to_vehicles(plates_data)
                
                # Safety detection (includes lane detection when enabled)
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        speed = track_data.get('speed')
                        bbox = track_data.get('bbox')
                        
                        if speed is not None and bbox is not None:
                            safety_detector.update_vehicle_state(track_id, bbox, speed)
                    
                # Process frame with lane detection enabled
                frame_alerts = safety_detector.process_frame(current_tracks, frame=frame)
                
                # Record violations by track_id
                if frame_alerts:
                    for alert in frame_alerts:
                        track_id = alert.get('track_id')
                        if track_id and track_id in current_tracks:
                            integrator.add_violation(track_id, alert)
                
                speed_viols = len(integrator.get_speed_violations())
                lane_viols = len(integrator.get_lane_violations())
                
                if frame_count % 30 == 0:  # Log every 30 frames
                    print(f"[INFO] Frame {frame_count}: Speed violations: {speed_viols}, Lane violations: {lane_viols}")
                
                # Process every 2nd frame to speed up
                if frame_count % 2 == 0:
                    continue
                    
            except Exception as frame_error:
                print(f"[ERROR] Frame {frame_count} processing failed: {frame_error}")
                traceback.print_exc()
                # Continue with next frame instead of stopping
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

# Traffic Detection Endpoints

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
        
        # Convert to JSON-friendly format
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


# Ingest parking record(s) (JSON)
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
##
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


# --- ML / Accident detection endpoints (from Ishani branch) ---
@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from IoT devices (ESP32)"""
    try:
        data = request.get_json()
        required_fields = ['device_id', 'distance', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        device_id = data['device_id']
        distance = float(data['distance'])
        impact_detected = int(data.get('impact_detected', 0))
        total_impacts = int(data.get('total_impacts', 0))
        location = data['location']
        timestamp = data.get('timestamp', datetime.now().isoformat())

        connected_devices[device_id] = {
            'device_id': device_id,
            'location': location,
            'status': 'online',
            'last_seen': datetime.now().isoformat(),
            'distance': distance,
            'impact_detected': impact_detected,
            'total_impacts': total_impacts
        }

        accident = detector.analyze_sensor_data(device_id, distance, impact_detected, total_impacts, location, timestamp)
##
        if accident:
            accident['confirmed'] = True
            try:
                send_accident_alert(accident)
            except Exception as e:
                logging.warning(f"Failed to send email alert: {e}")

        return jsonify({
            "success": True,
            "message": "Sensor data received and analyzed",
            "accident_detected": accident is not None,
            "accident": accident
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

                

        return jsonify({
            "success": True,
            "message": "Sensor data received and analyzed",
            "accident_detected": accident is not None,
            "accident": accident
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/accidents', methods=['GET'])
def get_accidents():
    """Get all accidents"""
    try:
        hours = request.args.get('hours', type=int, default=24)
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = []
        for a in detector.accident_log:
            try:
                timestamp_str = a.get('timestamp', '')
                if not timestamp_str:
                    continue
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    try:
                        ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        filtered.append(a)
                        continue
                if ts > cutoff:
                    filtered.append(a)
            except Exception as e:
                logging.warning(f"Error filtering accident: {e}")
                continue

        severity_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        for acc in filtered:
            severity = acc.get('severity', 'low')
            if severity in severity_counts:
                severity_counts[severity] += 1

        return jsonify({
            "success": True,
            "accidents": filtered,
            "total_count": len(filtered),
            "severity_counts": severity_counts,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Error in get_accidents: {e}")
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get alerts"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        filtered_alerts = alerts
        if unread_only:
            filtered_alerts = [a for a in alerts if not a['read']]
        return jsonify({"success": True, "alerts": filtered_alerts, "unread_count": len([a for a in alerts if not a['read']])})
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
                timestamp_str = a.get('timestamp', '')
                if not timestamp_str:
                    continue
                try:
                    ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    try:
                        ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue
                if ts > last_24h:
                    recent_accidents.append(a)
            except Exception as e:
                logging.warning(f"Error processing accident in statistics: {e}")
                continue

        stats = {
            "total_accidents": len(detector.accident_log),
            "accidents_last_24h": len(recent_accidents),
            "active_alerts": len([a for a in alerts if not a['read']]),
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
        for alert in alerts[-100:]:  # Last 100 alerts
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
        
        # Validate video path
        if not video_path:
            return jsonify({
                "success": False,
                "error": "No video path provided"
            }), 400
        
        # Convert relative path to absolute path from project root
        if not os.path.isabs(video_path):
            project_root = Path(__file__).parent.parent
            video_path = str(project_root / video_path)
            print(f"[INFO] Converted to absolute path: {video_path}")
            
        if not os.path.exists(video_path):
            return jsonify({
                "success": False,
                "error": f"Video file not found: {video_path}"
            }), 400
        
        # Test if OpenCV can open the video
        test_cap = cv2.VideoCapture(video_path)
        if not test_cap.isOpened():
            test_cap.release()
            return jsonify({
                "success": False,
                "error": f"Cannot open video file. Check if the file is a valid video format: {video_path}"
            }), 400
        test_cap.release()
        
        # Stop any existing processing
        if current_session['is_processing']:
            current_session['is_processing'] = False
            if current_session['processing_thread']:
                current_session['processing_thread'].join(timeout=2)
        
        # Initialize fresh session
        print(f"[INFO] Initializing detection session for: {video_path}")
        
        try:
            print("[INFO] Creating VehicleDataIntegrator...")
            current_session['integrator'] = VehicleDataIntegrator(speed_limit=60)
            
            print("[INFO] Creating SafetyEventDetector with lane detection...")
            current_session['safety_detector'] = SafetyEventDetector(enable_lane_detection=True)
            
            print(f"[INFO] Creating VehicleSpeedDetector with video: {video_path}")
            # Initialize speed detector in headless mode (no GUI windows)
            current_session['speed_detector'] = VehicleSpeedDetector(headless=True)
            
            print("[INFO] Creating NumberPlateDetector...")
            # Initialize ANPR detector with required model_path
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
        
        # Start processing in background thread
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
        
        # Wait for thread to finish
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
        export_format = data.get('format', 'csv')  # csv, json, violations
        
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


# Google Sheets / Historical Data Endpoints

@app.route('/api/violations/history', methods=['GET'])
def get_violation_history():
    """Get historical violations from Google Sheets"""
    try:
        # Get recent violations (last 24 hours)
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
        }), 200  # Still return 200 to avoid frontend errors
##

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

# Add /api/parking-data for compatibility with devinda branch
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
    ##
    try:
         # Get parking data       
        parking_data = _get_parking_data()
        occupied = sum(1 for p in parking_data if (p.get('status') or p.get('Status') or '').upper() == 'OCCUPIED')
        
        # Get detection status
        detection_active = current_session.get('is_processing', False)
        
        # Get recent violations
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


# Error Handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# Mark an action (dispatch or resolve) against a device/record
@app.route('/api/mark-action', methods=['POST'])
def mark_action():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        # Accept single or list
        actions = payload if isinstance(payload, list) else [payload]
        appended = 0
        for act in actions:
            ok = sheets_handler.append_action(act)
            if ok:
                appended += 1

        return jsonify({"success": True, "appended": appended}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
##
# --- Email alert function ---
def send_accident_alert(accident):
    """Send an alert email when an accident is detected.

    The function logs its activity and swallows exceptions so callers
    don't crash the request handler.
    """
    try:
        sender_email = "madhukaishani123@gmail.com"
        receiver_email = "ishanimadhuka12345@gmail.com"
        app_password = "ejhtatmzqwkhqvyl"  

        msg = EmailMessage()
        msg["Subject"] = "🚨 Accident Detected!"
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg.set_content(
            f"An accident has been detected!\n\n"
            f"Device ID: {accident['device_id']}\n"
            f"Location: {accident['location']}\n"
            f"Timestamp: {accident['timestamp']}\n"
            f"Distance: {accident['distance']}\n"
            f"Distance: {accident['distance']}\n"
            f"Impact Detected: {accident['impact_detected']}\n"
            f"Total Impacts: {accident['total_impacts']}"
        )

        # Send email via Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        logging.info("✅ Accident alert email sent to %s", receiver_email)
    except Exception as e:
        logging.error("Failed to send accident alert email: %s", e)
        logging.debug(traceback.format_exc())


# --- FastAPI Routing App (Incident-Aware Rerouting) ---
from services.rerouting_engine import (
    load_graph,
    load_edges_dataset,
    load_incidents,
    build_routing_graph,
    apply_incident_penalties,
    find_nearest_node_with_distance,
    calculate_shortest_path,
    calculate_multiple_routes,
    get_route_coordinates,
    get_corridor_subgraph,
    filter_edges_for_subgraph,
    get_route_summary,
    haversine_distance
)

fastapi_app = FastAPI()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_GRAPH = load_graph()
EDGES_DF = load_edges_dataset()

INCIDENTS_FILE = os.path.join("data", "incidents", "manual_incidents.csv")


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    vehicle_type: str
    origin_name: str | None = None
    destination_name: str | None = None


class IncidentReportRequest(BaseModel):
    type: str
    severity: str
    lat: float
    lng: float
    description: str = ""


@fastapi_app.get("/")
def fastapi_home():
    return {"message": "Sri Lanka Incident-Aware Routing API is running"}


def save_incident_report(report: IncidentReportRequest):
    os.makedirs(os.path.dirname(INCIDENTS_FILE), exist_ok=True)

    # determine next incident id
    next_id = 1

    if os.path.exists(INCIDENTS_FILE):
        try:
            df = pd.read_csv(INCIDENTS_FILE)

            if not df.empty and "incident_id" in df.columns:
                next_id = int(df["incident_id"].max()) + 1

        except Exception:
            next_id = 1

    file_exists = os.path.exists(INCIDENTS_FILE)

    with open(INCIDENTS_FILE, "a", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "incident_id",
                "type",
                "severity",
                "lat",
                "lng",
                "status",
                "description",
                "timestamp"
            ])

        writer.writerow([
            next_id,
            report.type,
            report.severity,
            report.lat,
            report.lng,
            "active",
            report.description,
            datetime.now().isoformat()
        ])


def build_graph_for_request(request: RouteRequest):
    straight_distance_m = haversine_distance(
        request.origin_lat,
        request.origin_lng,
        request.dest_lat,
        request.dest_lng
    )

    long_distance_mode = straight_distance_m > 30000

    if long_distance_mode:
        buffer_deg = 0.12
        max_route_points = 80
    else:
        buffer_deg = 0.08
        max_route_points = 120

    sub_base_graph = get_corridor_subgraph(
        BASE_GRAPH,
        request.origin_lat,
        request.origin_lng,
        request.dest_lat,
        request.dest_lng,
        buffer_deg=buffer_deg
    )

    sub_edges_df = filter_edges_for_subgraph(EDGES_DF, sub_base_graph)
    current_hour = datetime.now().hour

    routing_graph = build_routing_graph(
        sub_base_graph,
        sub_edges_df,
        request.vehicle_type,
        current_hour
    )

    # load and apply incidents
    incidents_df = load_incidents()
    active_incident_count = apply_incident_penalties(routing_graph, incidents_df)

    return routing_graph, long_distance_mode, max_route_points, active_incident_count


@fastapi_app.get("/api/incidents")
def get_active_incidents():
    incidents_df = load_incidents()

    return {
        "success": True,
        "count": len(incidents_df),
        "incidents": incidents_df.to_dict(orient="records")
    }


@fastapi_app.post("/api/incidents/report")
def report_incident(report: IncidentReportRequest):
    save_incident_report(report)

    return {
        "success": True,
        "message": "Incident report saved successfully."
    }


@fastapi_app.post("/api/traffic/analyze-route")
def analyze_route(request: RouteRequest):
    routing_graph, long_distance_mode, max_route_points, active_incident_count = build_graph_for_request(request)

    print("Primary route request")
    print("Long distance mode:", long_distance_mode)
    print("Graph nodes:", len(routing_graph.nodes))
    print("Graph edges:", len(routing_graph.edges))
    print("Active incidents affecting graph:", active_incident_count)

    start_node, start_snap_distance = find_nearest_node_with_distance(
        routing_graph, request.origin_lat, request.origin_lng
    )
    end_node, end_snap_distance = find_nearest_node_with_distance(
        routing_graph, request.dest_lat, request.dest_lng
    )

    print("Origin:", request.origin_name, request.origin_lat, request.origin_lng)
    print("Destination:", request.destination_name, request.dest_lat, request.dest_lng)
    print("Start snap distance (m):", start_snap_distance)
    print("End snap distance (m):", end_snap_distance)

    MAX_SNAP_DISTANCE_METERS = 5000

    if start_snap_distance > MAX_SNAP_DISTANCE_METERS:
        return {
            "success": False,
            "error": "The starting point is too far from a mapped road in the Sri Lanka road network."
        }

    if end_snap_distance > MAX_SNAP_DISTANCE_METERS:
        return {
            "success": False,
            "error": "The destination is too far from a mapped road in the Sri Lanka road network."
        }

    primary_path, primary_time_sec, primary_distance_m, primary_free_flow_sec = calculate_shortest_path(
        routing_graph,
        start_node,
        end_node
    )

    if not primary_path:
        return {
            "success": False,
            "error": "No route could be found between these locations."
        }

    primary_distance_km = round(primary_distance_m / 1000, 2)
    primary_time_min = round(primary_time_sec / 60, 2)
    normal_duration = round(primary_free_flow_sec / 60, 2)

    primary_coords = get_route_coordinates(
        routing_graph,
        primary_path,
        max_points=max_route_points
    )

    delay_minutes = max(0, round(primary_time_min - normal_duration, 2))

    if delay_minutes < 5:
        congestion_level = "light"
    elif delay_minutes < 15:
        congestion_level = "moderate"
    else:
        congestion_level = "heavy"

    delay_percentage = round(
        ((delay_minutes / normal_duration) * 100) if normal_duration > 0 else 0,
        2
    )

    return {
        "success": True,
        "analysis": {
            "origin": request.origin_name or "Current Location",
            "destination": request.destination_name or "Destination",
            "vehicle_type": request.vehicle_type,
            "analysis_time": datetime.now().isoformat(),
            "routing_source": "sri_lanka_incident_aware_engine",
            "long_distance_mode": long_distance_mode,

            "incident_info": {
                "active_incident_count": active_incident_count
            },

            "origin_coords": {
                "lat": request.origin_lat,
                "lng": request.origin_lng
            },
            "destination_coords": {
                "lat": request.dest_lat,
                "lng": request.dest_lng
            },

            "congestion": {
                "level": congestion_level
            },

            "primary_route": {
                "distance_text": f"{primary_distance_km} km",
                "normal_duration": normal_duration,
                "traffic_duration": primary_time_min,
                "delay_minutes": delay_minutes,
                "delay_percentage": delay_percentage,
                "summary": get_route_summary(routing_graph, primary_path),
                "coordinates": primary_coords
            },

            "recommendation": {
                "should_reroute": False,
                "alternative": None
            },

            "alternatives": []
        }
    }


@fastapi_app.post("/api/traffic/alternative-routes")
def alternative_routes(request: RouteRequest):
    routing_graph, long_distance_mode, max_route_points, active_incident_count = build_graph_for_request(request)

    if long_distance_mode:
        return {
            "success": True,
            "incident_info": {
                "active_incident_count": active_incident_count
            },
            "alternatives": []
        }

    print("Alternative routes request")
    print("Active incidents affecting graph:", active_incident_count)

    start_node, _ = find_nearest_node_with_distance(
        routing_graph, request.origin_lat, request.origin_lng
    )
    end_node, _ = find_nearest_node_with_distance(
        routing_graph, request.dest_lat, request.dest_lng
    )

    raw_routes = calculate_multiple_routes(
        routing_graph,
        start_node,
        end_node,
        k=2
    )

    alternatives = []

    for route in raw_routes[1:]:
        distance_km = round(route["distance_m"] / 1000, 2)
        alt_normal_min = round(route["free_flow_time_sec"] / 60, 2)
        time_min = round(route["travel_time_sec"] / 60, 2)
        alt_delay = max(0, round(time_min - alt_normal_min, 2))

        if alt_delay < 5:
            alt_level = "light"
        elif alt_delay < 15:
            alt_level = "moderate"
        else:
            alt_level = "heavy"

        alternatives.append({
            "summary": get_route_summary(routing_graph, route["path"]),
            "distance_text": f"{distance_km} km",
            "normal_duration": alt_normal_min,
            "traffic_duration": time_min,
            "delay_minutes": alt_delay,
            "delay_percentage": round(((alt_delay / alt_normal_min) * 100), 2) if alt_normal_min > 0 else 0,
            "traffic_level": alt_level,
            "coordinates": get_route_coordinates(
                routing_graph,
                route["path"],
                max_points=max_route_points
            )
        })

    return {
        "success": True,
        "incident_info": {
            "active_incident_count": active_incident_count
        },
        "alternatives": alternatives
    }


if __name__ == '__main__':
    logging.info("Starting Traffic Management + ML Accident Detection API...")
    logging.info(f"ML Models loaded: {all([model_distance, model_impact, model_alert])}")
    logging.info(f"Google Sheets connected: {worksheet is not None}")
    app.run(debug=True, host='0.0.0.0', port=8000)

    