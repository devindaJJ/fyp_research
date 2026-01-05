from flask import Flask, jsonify, request
from flask_cors import CORS
from google_sheets import GoogleSheetsHandler
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize Google Sheets handler
sheets_handler = GoogleSheetsHandler()

@app.route('/')
def home():
    return jsonify({"message": "Traffic Management API is running!"})

# Get all parking data
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


# Ingest parking record(s) (JSON)
@app.route('/api/ingest-parking', methods=['POST'])
def ingest_parking():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"success": False, "error": "No JSON payload provided"}), 400

        # accept either a single record or a list of records
        records = payload if isinstance(payload, list) else [payload]
        appended = 0
        for rec in records:
            # Basic validation and normalization
            rec = rec or {}
            # Ensure timestamp exists
            if not rec.get('timestamp') and not rec.get('Time'):
                rec['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Derive Status if not provided
            if 'Status' not in rec and 'status' not in rec:
                dist = rec.get('distance') or rec.get('Distance') or rec.get('Distance_cm') or 9999
                try:
                    dval = float(dist)
                except Exception:
                    dval = 9999
                rec['Status'] = 'OCCUPIED' if dval < 200 else 'VACANT'

            sheets_handler.append_parking_record(rec)
            appended += 1

        return jsonify({"success": True, "appended": appended}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Get violation alerts
@app.route('/api/violations', methods=['GET'])
def get_violations():
    try:
        # Get last 24 hours violations
        time_threshold = datetime.now() - timedelta(hours=24)
        violations = sheets_handler.get_violations_since(time_threshold)
        
        return jsonify({
            "success": True,
            "violations": violations,
            "total_count": len(violations)
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
        stats = sheets_handler.get_system_statistics()
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Get device health status
@app.route('/api/device-health', methods=['GET'])
def get_device_health():
    try:
        health_data = sheets_handler.get_device_health()
        return jsonify({
            "success": True,
            "devices": health_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)