import cv2
import numpy as np
import base64
import tempfile
import os
import uuid
import time
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple

import pandas as pd
from io import StringIO
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from src.core.config import config
from src.speed.detector import VehicleSpeedDetector
from src.anpr.detector import NumberPlateDetector
from src.utils.integration import VehicleDataIntegrator
from src.utils.safety_detector import SafetyEventDetector
from src.utils.exporter import ResultExporter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ============================================================================
# Constants & Configuration
# ============================================================================

MAX_SESSIONS = 10
SESSION_TIMEOUT = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes
TEMP_DIR = tempfile.gettempdir()
MAX_VIDEO_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

# ============================================================================
# Session Management
# ============================================================================

class ProcessingSession:
    """Represents a video processing session"""
    
    def __init__(self, session_id: str):
        self.id = session_id
        self.video_path: Optional[str] = None
        self.status = "idle"  # idle, uploaded, processing, completed, error
        self.error_message: Optional[str] = None
        
        # Detectors
        self.speed_detector: Optional[VehicleSpeedDetector] = None
        self.anpr_detector: Optional[NumberPlateDetector] = None
        self.integrator: Optional[VehicleDataIntegrator] = None
        self.safety_detector: Optional[SafetyEventDetector] = None
        
        # Processing state
        self.results: List[Dict] = []
        self.frame_count = 0
        self.total_frames = 0
        self.processing_thread: Optional[threading.Thread] = None
        self.is_processing = False
        
        # Metadata
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.config: Dict = {
            'speed_limit': 60,
            'confidence_threshold': 0.25,
            'languages': ['en'],
            'anpr_model': 'models/number_plate_yolo.pt'
        }
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return (datetime.now() - self.created_at).total_seconds() > SESSION_TIMEOUT
    
    def get_progress(self) -> float:
        """Get processing progress percentage"""
        if self.total_frames == 0:
            return 0
        return (self.frame_count / self.total_frames) * 100
    
    def cleanup(self):
        """Clean up session resources"""
        try:
            # Stop processing
            self.is_processing = False
            if self.processing_thread:
                self.processing_thread.join(timeout=2)
            
            # Remove temp files
            if self.video_path and os.path.exists(self.video_path):
                os.remove(self.video_path)
                logger.info(f"Cleaned up video file: {self.video_path}")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")


class SessionManager:
    """Manages all active sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, ProcessingSession] = {}
        self.lock = threading.Lock()
        self._start_cleanup_thread()
    
    def create_session(self) -> str:
        """Create new session and return session ID"""
        with self.lock:
            if len(self.sessions) >= MAX_SESSIONS:
                raise Exception(f"Maximum concurrent sessions ({MAX_SESSIONS}) reached")
            
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = ProcessingSession(session_id)
            logger.info(f"Created session: {session_id}")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[ProcessingSession]:
        """Get session by ID"""
        with self.lock:
            return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session and cleanup"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].cleanup()
                del self.sessions[session_id]
                logger.info(f"Deleted session: {session_id}")
                return True
            return False
    
    def cleanup_expired(self):
        """Clean up expired sessions"""
        with self.lock:
            expired = [sid for sid, sess in self.sessions.items() if sess.is_expired()]
            for sid in expired:
                self.sessions[sid].cleanup()
                del self.sessions[sid]
                logger.warning(f"Cleaned up expired session: {sid}")
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        def cleanup_worker():
            while True:
                time.sleep(CLEANUP_INTERVAL)
                self.cleanup_expired()
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def get_all_sessions(self) -> List[Dict]:
        """Get summary of all sessions"""
        with self.lock:
            return [
                {
                    'session_id': sess.id,
                    'status': sess.status,
                    'created_at': sess.created_at.isoformat(),
                    'updated_at': sess.updated_at.isoformat(),
                    'frame_count': sess.frame_count,
                    'total_frames': sess.total_frames,
                    'progress': sess.get_progress()
                }
                for sess in self.sessions.values()
            ]


session_manager = SessionManager()

# ============================================================================
# Decorators & Middleware
# ============================================================================

def require_session(f):
    """Decorator to validate session_id in request"""
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = kwargs.get('session_id') or request.args.get('session_id')
        
        if not session_id:
            return jsonify({
                "success": False,
                "error": "session_id is required"
            }), 400
        
        session = session_manager.get_session(session_id)
        if not session:
            return jsonify({
                "success": False,
                "error": "Session not found or has expired"
            }), 404
        
        return f(*args, session=session, **kwargs)
    
    return decorated

def validate_json(*required_fields):
    """Decorator to validate JSON payload"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    "success": False,
                    "error": "Content-Type must be application/json"
                }), 400
            
            data = request.get_json()
            
            missing = [field for field in required_fields if field not in data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing)}"
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check API health and status"""
    return jsonify({
        "success": True,
        "status": "healthy",
        "service": "Traffic Management API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(session_manager.sessions)
    }), 200


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current system configuration"""
    return jsonify({
        "success": True,
        "config": {
            "max_sessions": MAX_SESSIONS,
            "session_timeout": SESSION_TIMEOUT,
            "max_video_size": MAX_VIDEO_SIZE
        }
    }), 200


# ============================================================================
# Session Management Endpoints
# ============================================================================

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all active sessions"""
    return jsonify({
        "success": True,
        "sessions": session_manager.get_all_sessions(),
        "total_count": len(session_manager.sessions)
    }), 200


@app.route('/api/sessions/<session_id>', methods=['GET'])
@require_session
def get_session_status(session_id, session):
    """Get detailed session status"""
    session.updated_at = datetime.now()
    
    return jsonify({
        "success": True,
        "session_id": session.id,
        "status": session.status,
        "error": session.error_message,
        "progress": session.get_progress(),
        "frame_count": session.frame_count,
        "total_frames": session.total_frames,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "config": session.config
    }), 200


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
@require_session
def delete_session(session_id, session):
    """Delete and cleanup a session"""
    session_manager.delete_session(session_id)
    
    return jsonify({
        "success": True,
        "message": f"Session {session_id} deleted and cleaned up"
    }), 200

# ============================================================================
# Video Upload & Processing
# ============================================================================

@app.route('/api/video/upload', methods=['POST'])
def upload_video():
    """Upload a video file for processing"""
    try:
        # Create new session
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        # Validate file
        if 'video' not in request.files:
            session_manager.delete_session(session_id)
            return jsonify({
                "success": False,
                "error": "No video file provided"
            }), 400
        
        video_file = request.files['video']
        
        if not video_file.filename:
            session_manager.delete_session(session_id)
            return jsonify({
                "success": False,
                "error": "Video filename is empty"
            }), 400
        
        # Validate file size
        video_file.seek(0, os.SEEK_END)
        file_size = video_file.tell()
        video_file.seek(0)
        
        if file_size > MAX_VIDEO_SIZE:
            session_manager.delete_session(session_id)
            return jsonify({
                "success": False,
                "error": f"Video file exceeds maximum size of {MAX_VIDEO_SIZE / (1024**3):.2f}GB"
            }), 413
        
        # Validate video format
        allowed_formats = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
        file_ext = Path(video_file.filename).suffix.lower()
        
        if file_ext not in allowed_formats:
            session_manager.delete_session(session_id)
            return jsonify({
                "success": False,
                "error": f"Unsupported video format. Allowed: {', '.join(allowed_formats)}"
            }), 400
        
        # Save video
        temp_dir = Path(TEMP_DIR) / session_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        video_path = temp_dir / video_file.filename
        video_file.save(str(video_path))
        
        # Verify video can be opened
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            session_manager.delete_session(session_id)
            return jsonify({
                "success": False,
                "error": "Invalid or corrupted video file"
            }), 400
        
        session.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        
        session.video_path = str(video_path)
        session.status = "uploaded"
        
        logger.info(f"Video uploaded for session {session_id}: {video_file.filename} ({file_size / (1024**2):.2f}MB)")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Video uploaded successfully",
            "filename": video_file.filename,
            "file_size": file_size,
            "total_frames": session.total_frames
        }), 201
        
    except Exception as e:
        logger.error(f"Video upload error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/video/process/<session_id>', methods=['POST'])
@require_session
@validate_json()
def start_processing(session_id, session):
    """Start processing a video"""
    try:
        if session.status == "processing":
            return jsonify({
                "success": False,
                "error": "Session is already processing"
            }), 400
        
        if session.status not in ["uploaded", "error"]:
            return jsonify({
                "success": False,
                "error": f"Cannot process video in {session.status} status"
            }), 400
        
        # Update config from request
        data = request.get_json() or {}
        session.config.update({
            'speed_limit': data.get('speed_limit', 60),
            'confidence_threshold': data.get('confidence_threshold', 0.25),
            'languages': data.get('languages', ['en']),
            'anpr_model': data.get('anpr_model', 'models/number_plate_yolo.pt')
        })
        
        # Initialize detectors
        try:
            logger.info(f"Initializing detectors for session {session_id}")
            
            session.integrator = VehicleDataIntegrator(
                speed_limit=session.config['speed_limit']
            )
            
            session.safety_detector = SafetyEventDetector()
            
            session.speed_detector = VehicleSpeedDetector(headless=True)
            
            anpr_model_path = Path(__file__).parent.parent / session.config['anpr_model']
            session.anpr_detector = NumberPlateDetector(
                model_path=str(anpr_model_path),
                languages=session.config['languages'],
                confidence_threshold=session.config['confidence_threshold']
            )
            
            logger.info(f"Detectors initialized successfully for session {session_id}")
            
        except Exception as init_error:
            session.status = "error"
            session.error_message = f"Detector initialization failed: {str(init_error)}"
            logger.error(session.error_message, exc_info=True)
            return jsonify({
                "success": False,
                "error": session.error_message
            }), 500
        
        # Start processing in background
        session.is_processing = True
        session.status = "processing"
        session.processing_thread = threading.Thread(
            target=_process_video_worker,
            args=(session,),
            daemon=True
        )
        session.processing_thread.start()
        
        logger.info(f"Video processing started for session {session_id}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Processing started",
            "status": "processing"
        }), 200
        
    except Exception as e:
        session.status = "error"
        session.error_message = str(e)
        logger.error(f"Processing start error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _process_video_worker(session: ProcessingSession):
    """Background worker for video processing"""
    try:
        cap = cv2.VideoCapture(session.video_path)
        if not cap.isOpened():
            raise Exception("Cannot open video file")
        
        logger.info(f"Starting processing for session {session.id}")
        
        frame_idx = 0
        while session.is_processing and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            try:
                frame_idx += 1
                session.frame_count = frame_idx
                
                # Detect vehicles
                detections = session.speed_detector.detect_vehicles(frame)
                tracks = session.speed_detector.tracker.update_tracks(detections, frame=frame)
                active_ids = session.speed_detector.process_tracks(tracks, frame)
                
                # ANPR detection
                plates_data = session.anpr_detector.detect_and_read(frame, draw_results=False)
                if isinstance(plates_data, tuple):
                    plates_data = plates_data[0]
                
                # Get current tracks
                current_tracks = session.speed_detector.get_current_tracks()
                
                # Update integrator
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        bbox = track_data.get('bbox')
                        speed = track_data.get('speed')
                        if bbox:
                            session.integrator.update_vehicle_tracking(track_id, bbox, speed)
                
                # Link plates
                if plates_data and isinstance(plates_data, list):
                    session.integrator.link_plates_to_vehicles(plates_data)
                
                # Safety detection
                if current_tracks and isinstance(current_tracks, dict):
                    for track_id, track_data in current_tracks.items():
                        speed = track_data.get('speed')
                        bbox = track_data.get('bbox')
                        if speed is not None and bbox is not None:
                            session.safety_detector.update_vehicle_state(track_id, bbox, speed)
                    
                    safety_alerts = session.safety_detector.process_frame(current_tracks)
                
                # Store results every N frames
                if frame_idx % 10 == 0:
                    result = {
                        'frame': frame_idx,
                        'timestamp': datetime.now().isoformat(),
                        'vehicles_count': len(current_tracks) if current_tracks else 0,
                        'violations_count': len(session.integrator.get_violations()),
                        'plates_detected': len(plates_data) if plates_data else 0
                    }
                    session.results.append(result)
                    
            except Exception as frame_error:
                logger.warning(f"Frame {frame_idx} processing error: {frame_error}")
                continue
        
        cap.release()
        session.status = "completed"
        session.is_processing = False
        logger.info(f"Processing completed for session {session.id}: {frame_idx} frames")
        
    except Exception as e:
        session.status = "error"
        session.error_message = str(e)
        session.is_processing = False
        logger.error(f"Processing worker error: {e}", exc_info=True)


# ============================================================================
# Results & Data Endpoints
# ============================================================================

@app.route('/api/results/<session_id>/vehicles', methods=['GET'])
@require_session
def get_vehicles(session_id, session):
    """Get all tracked vehicles"""
    if not session.integrator:
        return jsonify({
            "success": False,
            "error": "Session has no processing data"
        }), 400
    
    try:
        vehicles = session.integrator.get_all_vehicles()
        vehicle_list = [
            {
                'track_id': track_id,
                'speed': data.get('speed'),
                'plate': data.get('plate'),
                'violation': data.get('violation'),
                'bbox': data.get('bbox')
            }
            for track_id, data in vehicles.items()
        ]
        
        return jsonify({
            "success": True,
            "vehicles": vehicle_list,
            "total_count": len(vehicle_list),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching vehicles: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/results/<session_id>/violations', methods=['GET'])
@require_session
def get_violations(session_id, session):
    """Get speeding violations"""
    if not session.integrator:
        return jsonify({
            "success": False,
            "error": "Session has no processing data"
        }), 400
    
    try:
        violations = session.integrator.get_violations()
        
        return jsonify({
            "success": True,
            "violations": violations,
            "total_count": len(violations),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching violations: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/results/<session_id>/safety-alerts', methods=['GET'])
@require_session
def get_safety_alerts(session_id, session):
    """Get safety alerts"""
    if not session.safety_detector:
        return jsonify({
            "success": False,
            "error": "Session has no safety data"
        }), 400
    
    try:
        limit = request.args.get('limit', type=int, default=100)
        alerts = session.safety_detector.alerts[-limit:]
        
        alert_list = [
            {
                'type': alert['type'],
                'severity': alert['severity'],
                'track_ids': alert.get('track_ids', []),
                'description': alert['description'],
                'timestamp': alert['timestamp'].isoformat()
            }
            for alert in alerts
        ]
        
        return jsonify({
            "success": True,
            "alerts": alert_list,
            "total_count": len(session.safety_detector.alerts),
            "collisions_count": len(session.safety_detector.collisions),
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching safety alerts: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/results/<session_id>/summary', methods=['GET'])
@require_session
def get_summary(session_id, session):
    """Get summary statistics"""
    try:
        vehicles = session.integrator.get_all_vehicles() if session.integrator else {}
        violations = session.integrator.get_violations() if session.integrator else []
        
        summary = {
            'total_frames_processed': session.frame_count,
            'total_frames': session.total_frames,
            'progress': session.get_progress(),
            'vehicles_tracked': len(vehicles),
            'vehicles_with_speed': sum(1 for v in vehicles.values() if v.get('speed')),
            'vehicles_with_plate': sum(1 for v in vehicles.values() if v.get('plate')),
            'speeding_violations': len(violations),
            'safety_alerts': len(session.safety_detector.alerts) if session.safety_detector else 0,
            'collisions': len(session.safety_detector.collisions) if session.safety_detector else 0
        }
        
        return jsonify({
            "success": True,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# Export Endpoints
# ============================================================================

@app.route('/api/export/<session_id>/<format>', methods=['GET'])
@require_session
def export_results(session_id, session, format):
    """Export results in specified format"""
    if not session.integrator:
        return jsonify({
            "success": False,
            "error": "No processing data to export"
        }), 400
    
    try:
        vehicles = session.integrator.get_all_vehicles()
        exporter = ResultExporter()
        
        if format == 'csv':
            path = exporter.export_to_csv(vehicles)
            return send_file(path, as_attachment=True, download_name=f"results_{session_id}.csv")
        
        elif format == 'json':
            path = exporter.export_to_json(vehicles)
            return send_file(path, as_attachment=True, download_name=f"results_{session_id}.json")
        
        elif format == 'violations':
            path = exporter.export_violations_only(vehicles)
            return send_file(path, as_attachment=True, download_name=f"violations_{session_id}.csv")
        
        else:
            return jsonify({
                "success": False,
                "error": f"Unsupported format: {format}. Allowed: csv, json, violations"
            }), 400
            
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.before_request
def log_request():
    """Log incoming requests"""
    logger.debug(f"{request.method} {request.path}")


@app.teardown_appcontext
def cleanup_on_shutdown(error=None):
    """Cleanup on app shutdown"""
    logger.info("Cleaning up all sessions...")
    for session_id in list(session_manager.sessions.keys()):
        session_manager.delete_session(session_id)


if __name__ == '__main__':
    logger.info("Starting Traffic Management API v2.0.0...")
    app.run(debug=True, host='0.0.0.0', port=8000)