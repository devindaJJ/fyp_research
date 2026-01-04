import sys
import os
import json
import cv2
import threading
import time
import logging
import joblib
import gspread
import traceback
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


app = Flask(__name__)
CORS(app)  

# Register blueprints
app.register_blueprint(traffic_bp)

sheets_handler = None

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
                
                # Safety detection
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        speed = track_data.get('speed')
                        bbox = track_data.get('bbox')
                        
                        if speed is not None and bbox is not None:
                            safety_detector.update_vehicle_state(track_id, bbox, speed)
                    
                alerts = safety_detector.process_frame(current_tracks)
                print(f"[INFO] Processed {frame_count} frames, {len(integrator.get_violations())} violations")
                
                # Process every 2nd frame to speed up
                if frame_count % 2 == 0:
                    continue
                    
            except Exception as frame_error:
                print(f"[ERROR] Frame {frame_count} processing failed: {frame_error}")
                import traceback
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
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


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
        import traceback
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
        import traceback
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
            
            print("[INFO] Creating SafetyEventDetector...")
            current_session['safety_detector'] = SafetyEventDetector()
            
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
            import traceback
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
        
        stats = {
            'total_vehicles_tracked': len(vehicles),
            'vehicles_with_speed': sum(1 for v in vehicles.values() if v['speed'] is not None),
            'vehicles_with_plate': sum(1 for v in vehicles.values() if v['plate'] is not None),
            'speeding_violations': len(violations),
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


@app.route('/api/system/overview', methods=['GET'])
def get_system_overview():
    """Get complete system overview"""
    try:
        # Get parking data
        parking_data = sheets_handler.get_parking_data()
        occupied = sum(1 for p in parking_data if p.get('status') == 'OCCUPIED')
        
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

if __name__ == '__main__':
    logging.info("Starting Traffic Management + ML Accident Detection API...")
    logging.info(f"ML Models loaded: {all([model_distance, model_impact, model_alert])}")
    logging.info(f"Google Sheets connected: {worksheet is not None}")
    app.run(debug=True, host='0.0.0.0', port=8000)