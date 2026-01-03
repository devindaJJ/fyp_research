from flask import Flask, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import threading
import time
import random
from collections import deque

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# In-memory storage for accidents and vibration data
accidents = []
vibration_data_history = deque(maxlen=1000)  # Store last 1000 readings
alerts = []
connected_devices = {}

# Configuration
ACCIDENT_THRESHOLD = 100.0  # Hz threshold for accident detection
NORMAL_VIBRATION_RANGE = (5.0, 30.0)  # Normal vibration range in Hz
ACCIDENT_COOLDOWN = 60  # seconds before allowing another accident from same device

class AccidentDetector:
    def __init__(self):
        self.accident_log = []
        self.device_last_accident = {}
        self.running = True
        
    def analyze_vibration(self, device_id, vibration_hz, location, timestamp):
        """Analyze vibration data to detect accidents"""
        
        # Store vibration data
        vibration_data_history.append({
            "device_id": device_id,
            "vibration_hz": vibration_hz,
            "location": location,
            "timestamp": timestamp
        })
        
        # Check for accident conditions
        is_accident = False
        severity = "low"
        
        if vibration_hz > ACCIDENT_THRESHOLD:
            is_accident = True
            severity = "critical"
        elif vibration_hz > ACCIDENT_THRESHOLD * 0.7:
            is_accident = True
            severity = "high"
        elif vibration_hz > ACCIDENT_THRESHOLD * 0.5:
            is_accident = True
            severity = "medium"
        
        # Check cooldown period
        if is_accident and device_id in self.device_last_accident:
            last_accident_time = self.device_last_accident[device_id]
            time_diff = (datetime.now() - last_accident_time).total_seconds()
            if time_diff < ACCIDENT_COOLDOWN:
                return None  # Still in cooldown
        
        if is_accident:
            # Log the accident
            accident = {
                "id": f"acc_{device_id}_{int(time.time())}",
                "device_id": device_id,
                "vibration_hz": vibration_hz,
                "severity": severity,
                "location": location,
                "timestamp": timestamp,
                "status": "detected",
                "confirmed": False,
                "responded": False
            }
            
            self.accident_log.append(accident)
            self.device_last_accident[device_id] = datetime.now()
            
            # Create alert
            alert = {
                "id": f"alert_{device_id}_{int(time.time())}",
                "type": "accident",
                "title": f"Accident Detected - {severity.upper()}",
                "message": f"High vibration ({vibration_hz:.2f} Hz) detected at {location}",
                "severity": severity,
                "device_id": device_id,
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "read": False,
                "accident_id": accident["id"]
            }
            
            alerts.append(alert)
            
            # Keep only last 100 alerts
            if len(alerts) > 100:
                alerts.pop(0)
            
            return accident
        
        return None

# Initialize detector
detector = AccidentDetector()

# Simulate device data (replace with actual IoT device connections)
def simulate_device_data():
    """Simulate IoT devices sending vibration data"""
    locations = [
        "Main Road Junction A",
        "Highway Section B",
        "Downtown Intersection",
        "Bridge Approach",
        "Tunnel Entrance",
        "School Zone"
    ]
    
    devices = [
        {"id": "device_001", "type": "vibration_sensor", "location": locations[0]},
        {"id": "device_002", "type": "vibration_sensor", "location": locations[1]},
        {"id": "device_003", "type": "vibration_sensor", "location": locations[2]},
        {"id": "device_004", "type": "accelerometer", "location": locations[3]},
        {"id": "device_005", "type": "seismic_sensor", "location": locations[4]}
    ]
    
    while detector.running:
        try:
            for device in devices:
                # Simulate normal traffic vibration (5-30 Hz)
                base_vibration = random.uniform(5.0, 30.0)
                
                # Occasionally simulate accidents (1% chance)
                if random.random() < 0.01:
                    vibration = random.uniform(80.0, 200.0)  # Accident vibration
                else:
                    vibration = base_vibration + random.uniform(-2.0, 2.0)
                
                # Update device status
                connected_devices[device["id"]] = {
                    "device_id": device["id"],
                    "type": device["type"],
                    "location": device["location"],
                    "status": "online",
                    "last_seen": datetime.now().isoformat(),
                    "current_vibration": vibration,
                    "battery": random.randint(60, 100)
                }
                
                # Analyze for accidents
                detector.analyze_vibration(
                    device["id"],
                    vibration,
                    device["location"],
                    datetime.now().isoformat()
                )
            
            time.sleep(5)  # Simulate 5-second intervals
            
        except Exception as e:
            print(f"Error in device simulation: {e}")
            time.sleep(10)

# Start simulation in background thread
simulation_thread = threading.Thread(target=simulate_device_data, daemon=True)
simulation_thread.start()

@app.route('/')
def home():
    return jsonify({
        "message": "Accident Detection API is running!",
        "endpoints": {
            "accidents": "/api/accidents",
            "alerts": "/api/alerts",
            "vibration_data": "/api/vibration-data",
            "devices": "/api/devices",
            "statistics": "/api/statistics"
        }
    })

# Receive vibration data from IoT devices
@app.route('/api/vibration-data', methods=['POST'])
def receive_vibration_data():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
        
        required_fields = ['device_id', 'vibration_hz', 'location']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Update device status
        connected_devices[data['device_id']] = {
            "device_id": data['device_id'],
            "type": data.get('type', 'vibration_sensor'),
            "location": data['location'],
            "status": "online",
            "last_seen": datetime.now().isoformat(),
            "current_vibration": data['vibration_hz'],
            "battery": data.get('battery', 100)
        }
        
        # Analyze for accidents
        timestamp = data.get('timestamp', datetime.now().isoformat())
        accident = detector.analyze_vibration(
            data['device_id'],
            float(data['vibration_hz']),
            data['location'],
            timestamp
        )
        
        response = {
            "success": True,
            "message": "Vibration data received",
            "accident_detected": accident is not None
        }
        
        if accident:
            response["accident"] = accident
            response["alert_id"] = f"alert_{data['device_id']}_{int(time.time())}"
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Get all accidents
@app.route('/api/accidents', methods=['GET'])
def get_accidents():
    try:
        # Filter by time if specified
        hours = request.args.get('hours', type=int)
        filtered_accidents = detector.accident_log
        
        if hours:
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered_accidents = [
                a for a in detector.accident_log
                if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > cutoff
            ]
        
        return jsonify({
            "success": True,
            "accidents": filtered_accidents,
            "total_count": len(filtered_accidents),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Get real-time alerts
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        severity_filter = request.args.get('severity')
        
        filtered_alerts = alerts
        
        if unread_only:
            filtered_alerts = [a for a in alerts if not a['read']]
        
        if severity_filter:
            filtered_alerts = [a for a in filtered_alerts if a['severity'] == severity_filter]
        
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

# Mark alert as read
@app.route('/api/alerts/<alert_id>/read', methods=['PUT'])
def mark_alert_read(alert_id):
    try:
        for alert in alerts:
            if alert['id'] == alert_id:
                alert['read'] = True
                return jsonify({
                    "success": True,
                    "message": "Alert marked as read"
                })
        
        return jsonify({
            "success": False,
            "error": "Alert not found"
        }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Update accident status
@app.route('/api/accidents/<accident_id>/status', methods=['PUT'])
def update_accident_status(accident_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        confirmed = data.get('confirmed')
        
        if not new_status and confirmed is None:
            return jsonify({
                "success": False,
                "error": "No status or confirmed value provided"
            }), 400
        
        for accident in detector.accident_log:
            if accident['id'] == accident_id:
                if new_status:
                    accident['status'] = new_status
                if confirmed is not None:
                    accident['confirmed'] = bool(confirmed)
                
                return jsonify({
                    "success": True,
                    "accident": accident
                })
        
        return jsonify({
            "success": False,
            "error": "Accident not found"
        }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Get connected devices
@app.route('/api/devices', methods=['GET'])
def get_devices():
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

# Get vibration data history
@app.route('/api/vibration-data/history', methods=['GET'])
def get_vibration_history():
    try:
        device_id = request.args.get('device_id')
        limit = request.args.get('limit', type=int, default=100)
        
        filtered_data = list(vibration_data_history)
        
        if device_id:
            filtered_data = [d for d in filtered_data if d['device_id'] == device_id]
        
        filtered_data = filtered_data[-limit:]  # Get most recent
        
        return jsonify({
            "success": True,
            "data": filtered_data,
            "count": len(filtered_data)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Get system statistics
@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    try:
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        # Calculate statistics
        recent_accidents = [
            a for a in detector.accident_log
            if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > last_24h
        ]
        
        critical_accidents = [a for a in recent_accidents if a['severity'] == 'critical']
        
        # Get average vibration
        if vibration_data_history:
            recent_vibrations = list(vibration_data_history)[-100:]  # Last 100 readings
            avg_vibration = sum(d['vibration_hz'] for d in recent_vibrations) / len(recent_vibrations)
        else:
            avg_vibration = 0
        
        stats = {
            "total_accidents": len(detector.accident_log),
            "accidents_last_24h": len(recent_accidents),
            "critical_accidents": len(critical_accidents),
            "active_alerts": len([a for a in alerts if not a['read']]),
            "connected_devices": len(connected_devices),
            "avg_vibration_hz": avg_vibration,
            "accident_threshold": ACCIDENT_THRESHOLD,
            "system_uptime": "Running"
        }
        
        return jsonify({
            "success": True,
            "statistics": stats,
            "timestamp": now.isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Clear old data (for maintenance)
@app.route('/api/maintenance/clear-old', methods=['POST'])
def clear_old_data():
    try:
        days = request.args.get('days', type=int, default=30)
        cutoff = datetime.now() - timedelta(days=days)
        
        # Clear old accidents
        original_count = len(detector.accident_log)
        detector.accident_log = [
            a for a in detector.accident_log
            if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > cutoff
        ]
        
        # Clear old alerts
        original_alerts = len(alerts)
        alerts[:] = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) > cutoff
        ]
        
        return jsonify({
            "success": True,
            "message": f"Cleared data older than {days} days",
            "accidents_removed": original_count - len(detector.accident_log),
            "alerts_removed": original_alerts - len(alerts)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("Starting Accident Detection API Server...")
    print(f"Accident Threshold: {ACCIDENT_THRESHOLD} Hz")
    print(f"Normal Vibration Range: {NORMAL_VIBRATION_RANGE[0]}-{NORMAL_VIBRATION_RANGE[1]} Hz")
    app.run(debug=True, host='0.0.0.0', port=8000)