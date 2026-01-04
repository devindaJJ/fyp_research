import time
import logging
import joblib
import os
import gspread
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from collections import deque
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)  

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'src', 'models', 'trained')

logging.info(f"Looking for models in: {MODEL_PATH}")

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
    logging.error(f"Model files not found: {e}")
    logging.error(f"   Please ensure models are in: {MODEL_PATH}")
    model_distance = None
    model_impact = None
    model_alert = None
except Exception as e:
    logging.error(f"Error loading ML models: {e}")
    model_distance = None
    model_impact = None
    model_alert = None

accidents = []
vibration_data_history = deque(maxlen=1000)
alerts = []
connected_devices = {}
ml_predictions = []

ACCIDENT_THRESHOLD = 100.0
NORMAL_VIBRATION_RANGE = (5.0, 30.0)
ACCIDENT_COOLDOWN = 60

def init_google_sheets():
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(
            os.getenv('SERVICE_ACCOUNT_CREDS', '../keys/credentials.json'),
            scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet_id = os.getenv('SHEET_ID')
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet('AccidentLogs')
        return worksheet
    except Exception as e:
        logging.error(f"Google Sheets initialization error: {e}")
        return None

worksheet = init_google_sheets()

def load_accidents_from_sheets():
        """Load existing accidents from Google Sheets on startup"""
        if not worksheet:
            return
        
        try:
            records = worksheet.get_all_records()
            logging.info(f"Loading {len(records)} records from Google Sheets...")
            
            for record in records:
                try:
                    # Parse the record
                    timestamp = record.get('Timestamp', '')
                    device_id = record.get('Device ID', 'UNKNOWN')
                    distance = int(record.get('Distance (cm)', 0))
                    impact_detected = 1 if record.get('Impact Detected', 'NO') == 'YES' else 0
                    total_impacts = int(record.get('Total Impacts', 0))
                    location = record.get('Status', 'Unknown Location') 
                    alert_level_text = record.get('Alert Level', 'NORMAL')
                    
                    # Convert alert level text to number
                    alert_level_map = {'NORMAL': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
                    alert_level = alert_level_map.get(alert_level_text, 1)
                    
                    # Determine severity
                    severity_map = {0: 'low', 1: 'low', 2: 'medium', 3: 'high', 4: 'critical'}
                    severity = severity_map.get(alert_level, 'medium')
                    
                    # Create accident record
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
                    
                    # Update device status
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
                    logging.error(f"Error parsing record: {e}")
                    continue
            
            logging.info(f"Loaded {len(detector.accident_log)} accidents from Google Sheets")
            
        except Exception as e:
            logging.error(f"Error loading data from Google Sheets: {e}")

class MLAccidentDetector:
    def __init__(self):
        self.accident_log = []
        self.device_last_accident = {}
        self.running = True
            
    def predict_with_ml(self, distance, impact_detected, total_impacts):
        """Use ML models to predict accident characteristics"""
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
            logging.error(f"ML Prediction error: {e}")
            return None
    
    def analyze_sensor_data(self, device_id, distance, impact_detected, total_impacts, location, timestamp):
        """Analyze sensor data using ML models"""
        
        ml_pred = self.predict_with_ml(distance, impact_detected, total_impacts)
        
        if ml_pred:
            ml_predictions.append({
                'device_id': device_id,
                'timestamp': timestamp,
                'input': {'distance': distance, 'impact': impact_detected, 'total_impacts': total_impacts},
                'prediction': ml_pred
            })
            
            # Keep only last 500 predictions
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
                logging.error(f"Error logging to Google Sheets: {e}")
        
        return accident

detector = MLAccidentDetector()
load_accidents_from_sheets()

# API Routes
@app.route('/')
def home():
    return jsonify({
        "message": "ML-Powered Accident Detection API",
        "ml_models_loaded": all([model_distance, model_impact, model_alert]),
        "endpoints": {
            "accidents": "/api/accidents",
            "alerts": "/api/alerts",
            "sensor_data": "/api/sensor-data",
            "devices": "/api/devices",
            "statistics": "/api/statistics",
            "ml_predictions": "/api/ml-predictions"
        }
    })

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """Receive sensor data from IoT devices (ESP32)"""
    try:
        data = request.get_json()
        
        required_fields = ['device_id', 'distance', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Extract data
        device_id = data['device_id']
        distance = float(data['distance'])
        impact_detected = int(data.get('impact_detected', 0))
        total_impacts = int(data.get('total_impacts', 0))
        location = data['location']
        timestamp = data.get('timestamp', datetime.now().isoformat())
        
        # Update device status
        connected_devices[device_id] = {
            'device_id': device_id,
            'location': location,
            'status': 'online',
            'last_seen': datetime.now().isoformat(),
            'distance': distance,
            'impact_detected': impact_detected,
            'total_impacts': total_impacts
        }
        
        # Analyze with ML
        accident = detector.analyze_sensor_data(
            device_id, distance, impact_detected, total_impacts, location, timestamp
        )
        
        return jsonify({
            "success": True,
            "message": "Sensor data received and analyzed",
            "accident_detected": accident is not None,
            "accident": accident
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
                logging.error(f"Error filtering accident: {e}")
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
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get alerts"""
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        filtered_alerts = alerts
        if unread_only:
            filtered_alerts = [a for a in alerts if not a['read']]
        
        return jsonify({
            "success": True,
            "alerts": filtered_alerts,
            "unread_count": len([a for a in alerts if not a['read']])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/ml-predictions', methods=['GET'])
def get_ml_predictions():
    """Get recent ML predictions"""
    try:
        limit = request.args.get('limit', type=int, default=50)
        
        return jsonify({
            "success": True,
            "predictions": ml_predictions[-limit:],
            "count": len(ml_predictions)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

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
                logging.error(f"Error processing accident in statistics: {e}")
                continue
        
        stats = {
            "total_accidents": len(detector.accident_log),
            "accidents_last_24h": len(recent_accidents),
            "active_alerts": len([a for a in alerts if not a['read']]),
            "connected_devices": len(connected_devices),
            "ml_models_active": all([model_distance, model_impact, model_alert]),
            "total_predictions": len(ml_predictions)
        }
        
        return jsonify({
            "success": True,
            "statistics": stats,
            "timestamp": now.isoformat()
        })
    except Exception as e:
        logging.error(f"Error in get_statistics: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get connected devices"""
    try:
        return jsonify({
            "success": True,
            "devices": list(connected_devices.values()),
            "total_online": len(connected_devices)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    logging.info("Starting ML-Powered Accident Detection API...")
    logging.info(f"ML Models loaded: {all([model_distance, model_impact, model_alert])}")
    logging.info(f"Google Sheets connected: {worksheet is not None}")
    app.run(debug=True, host='0.0.0.0', port=8000)