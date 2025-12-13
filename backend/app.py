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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)