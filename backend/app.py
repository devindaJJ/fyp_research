from flask import Flask, jsonify, request
from flask_cors import CORS
# Support running as package (python -m backend.app) and as script (python backend/app.py)
try:
    from backend.google_sheets import GoogleSheetsHandler
    from backend.traffic_routes import traffic_bp
except Exception:
    from google_sheets import GoogleSheetsHandler
    from traffic_routes import traffic_bp
import json
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  

# Register blueprints
app.register_blueprint(traffic_bp)

sheets_handler = None

def get_sheets_handler():
    global sheets_handler
    if sheets_handler is None:
        try:
            sheets_handler = GoogleSheetsHandler()
        except Exception as e:
            print(f"Warning: Google Sheets initialization failed: {e}")
            return None
    return sheets_handler

@app.route('/')
def home():
    return jsonify({"message": "Traffic Management API is running!"})

# Get all parking data
@app.route('/api/parking-data', methods=['GET'])
def get_parking_data():
    try:
        handler = get_sheets_handler()
        if handler is None:
            return jsonify({
                "success": False,
                "error": "Google Sheets handler not available. Check credentials."
            }), 503
        data = handler.get_parking_data()
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
        handler = get_sheets_handler()
        if handler is None:
            return jsonify({
                "success": False,
                "error": "Google Sheets handler not available. Check credentials."
            }), 503
        # Get last 24 hours violations
        time_threshold = datetime.now() - timedelta(hours=24)
        violations = handler.get_violations_since(time_threshold)
        
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
        handler = get_sheets_handler()
        if handler is None:
            return jsonify({
                "success": False,
                "error": "Google Sheets handler not available. Check credentials."
            }), 503
        stats = handler.get_system_statistics()
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
        handler = get_sheets_handler()
        if handler is None:
            return jsonify({
                "success": False,
                "error": "Google Sheets handler not available. Check credentials."
            }), 503
        health_data = handler.get_device_health()
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
    app.run(debug=True, host='0.0.0.0', port=8000)