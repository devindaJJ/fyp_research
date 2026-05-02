"""
Lane Violation Detection Demo
Demonstrates integrated lane violation detection with speed violation system
using the lane 1.mp4 video
"""
import cv2
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.safety_detector import SafetyEventDetector
from src.utils.integration import VehicleDataIntegrator
from src.speed.detector import VehicleSpeedDetector
from src.anpr.detector import NumberPlateDetector


class LaneViolationDemo:
    """Demonstrates lane violation detection on video."""
    
    def __init__(self, video_path: str, speed_limit: float = 60.0, anpr_model: str = None):
        """
        Initialize the demo.
        
        Args:
            video_path: Path to video file
            speed_limit: Speed limit in km/h
            anpr_model: Path to ANPR model (optional)
        """
        self.video_path = video_path
        self.speed_limit = speed_limit
        
        # Initialize detectors
        print("[INFO] Initializing detectors...")
        self.speed_detector = VehicleSpeedDetector(video_path=video_path, speed_limit=speed_limit, headless=True)
        
        # ANPR detector (optional)
        self.anpr_detector = None
        if anpr_model and os.path.exists(anpr_model):
            try:
                self.anpr_detector = NumberPlateDetector(model_path=anpr_model)
                print("[INFO] ANPR detector initialized")
            except Exception as e:
                print(f"[WARNING] ANPR detector initialization failed: {e}")
        else:
            print("[INFO] ANPR detector disabled (model not found)")
        
        self.safety_detector = SafetyEventDetector(enable_lane_detection=True)
        self.integrator = VehicleDataIntegrator(speed_limit=speed_limit)
        
        print("[INFO] Detectors initialized successfully!")
    
    def process_video(self, skip_frames: int = 1, max_frames: int = None, display: bool = True):
        """
        Process video and detect violations.
        
        Args:
            skip_frames: Process every Nth frame
            max_frames: Maximum frames to process (None for all)
            display: Whether to display video with annotations
        """
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video: {self.video_path}")
            return
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"\n[INFO] Video Properties:")
        print(f"  Resolution: {width}x{height}")
        print(f"  FPS: {fps}")
        print(f"  Total Frames: {total_frames}")
        print(f"  Duration: {total_frames/fps:.1f}s")
        
        # Setup video writer for output (optional)
        output_path = None
        out = None
        if display:
            output_path = self.video_path.replace('.mp4', '_violations.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_count = 0
        violation_count = 0
        speed_violation_count = 0
        lane_violation_count = 0
        
        print(f"\n[INFO] Starting video processing...")
        print("="*80)
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Skip frames
                if frame_count % skip_frames != 0:
                    continue
                
                # Check max frames
                if max_frames and frame_count >= max_frames:
                    break
                
                try:
                    # Vehicle detection
                    detections = self.speed_detector.detect_vehicles(frame)
                    
                    # Track vehicles
                    tracks = self.speed_detector.tracker.update_tracks(detections, frame=frame)
                    active_ids = self.speed_detector.process_tracks(tracks, frame)
                    
                    # Get current tracks
                    current_tracks = self.speed_detector.get_current_tracks()
                    
                    # Update integrator
                    if current_tracks and isinstance(current_tracks, dict):
                        for track_id, track_data in current_tracks.items():
                            bbox = track_data.get('bbox')
                            speed = track_data.get('speed')
                            if bbox:
                                self.integrator.update_vehicle_tracking(track_id, bbox, speed)
                    
                    # ANPR detection
                    try:
                        if self.anpr_detector:
                            plates_data = self.anpr_detector.detect_and_read(frame, draw_results=False)
                            if isinstance(plates_data, tuple):
                                plates_data = plates_data[0]
                            if plates_data and isinstance(plates_data, list):
                                self.integrator.link_plates_to_vehicles(plates_data)
                    except Exception as anpr_error:
                        pass  # ANPR is optional
                    
                    # Safety detection with lane violation
                    frame_alerts = self.safety_detector.process_frame(current_tracks, frame)
                    
                    # Record violations in integrator
                    for alert in frame_alerts:
                        # Get track ID from alert
                        track_id = alert.get('track_id')
                        if track_id is not None:
                            self.integrator.add_violation(track_id, alert)
                            
                            if alert['type'] in ['ILLEGAL_LANE_CHANGE', 'EXCESSIVE_LANE_CHANGES', 'LANE_CROSSING']:
                                lane_violation_count += 1
                            elif 'SPEED' in alert['type'] or alert['type'] in ['AGGRESSIVE_ACCELERATION', 'HARD_BRAKING']:
                                speed_violation_count += 1
                            violation_count += 1
                    
                    # Display alerts
                    if frame_alerts:
                        print(f"\n[FRAME {frame_count}] {len(frame_alerts)} violation(s) detected:")
                        for alert in frame_alerts:
                            print(f"  - {alert['type']} (Track {alert.get('track_id', 'N/A')}): {alert['description']}")
                    
                    # Draw annotations on frame
                    if display and current_tracks:
                        frame = self._annotate_frame(frame, current_tracks, frame_alerts)
                        if out:
                            out.write(frame)
                        
                        # Display in window
                        cv2.imshow('Lane Violation Detection', frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    
                except Exception as e:
                    print(f"[WARNING] Frame {frame_count} processing error: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
            if output_path:
                print(f"\n[INFO] Output video saved: {output_path}")
        
        # Print summary
        self._print_summary(frame_count, violation_count, speed_violation_count, lane_violation_count)
    
    def _annotate_frame(self, frame, tracks, alerts):
        """
        Add annotations to frame showing detections and violations.
        
        Args:
            frame: Input frame
            tracks: Vehicle tracks dictionary
            alerts: List of alerts in this frame
            
        Returns:
            Annotated frame
        """
        # Draw vehicle boxes and info
        for track_id, track_data in tracks.items():
            bbox = track_data.get('bbox')
            if bbox:
                x1, y1, x2, y2 = bbox
                
                # Draw bounding box
                color = (0, 255, 0)  # Green
                
                # Check if vehicle has violations
                violations = self.integrator.vehicle_data.get(track_id, {}).get('lane_violations', [])
                if violations:
                    color = (0, 0, 255)  # Red for violations
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Add info
                speed = track_data.get('speed')
                plate = self.integrator.vehicle_data.get(track_id, {}).get('plate', 'N/A')
                
                info_text = f"ID:{track_id} Speed:{speed:.1f}km/h" if speed else f"ID:{track_id}"
                cv2.putText(frame, info_text, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw alerts at top
        y_offset = 30
        for alert in alerts:
            alert_text = f"{alert['type']}: {alert['description']}"
            cv2.putText(frame, alert_text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        
        return frame
    
    def _print_summary(self, total_frames, violations, speed_violations, lane_violations):
        """Print processing summary."""
        print("\n" + "="*80)
        print("[SUMMARY] Lane Violation Detection Results")
        print("="*80)
        print(f"Total Frames Processed: {total_frames}")
        print(f"Total Violations Detected: {violations}")
        print(f"  - Speed Violations: {speed_violations}")
        print(f"  - Lane Violations: {lane_violations}")
        
        print(f"\nViolation Details:")
        print(f"  Speed Violations: {len(self.integrator.get_speed_violations())}")
        print(f"  Lane Violations: {len(self.integrator.get_lane_violations())}")
        
        # Print per-vehicle summary
        print(f"\nVehicles with Violations:")
        for vehicle_data in self.integrator.vehicle_data.values():
            if vehicle_data.get('total_violations', 0) > 0:
                track_id = vehicle_data['track_id']
                total = vehicle_data['total_violations']
                lane_count = len(vehicle_data.get('lane_violations', []))
                plate = vehicle_data.get('plate', 'Unknown')
                print(f"  Track {track_id} (Plate: {plate}): {total} violations ({lane_count} lane-related)")
        
        print("="*80)


def main():
    """Main entry point."""
    # Video path
    video_path = r'c:\Users\hp\Documents\fyp_research\videos\lane 1.mp4'
    
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file not found: {video_path}")
        return
    
    # ANPR model path
    anpr_model = r'c:\Users\hp\Documents\fyp_research\models\number_plate_yolo.pt'
    
    # Create demo
    demo = LaneViolationDemo(video_path, speed_limit=60.0, anpr_model=anpr_model)
    
    # Process video
    print("\n[INFO] Starting Lane Violation Detection Demo")
    print(f"[INFO] Processing video: {os.path.basename(video_path)}")
    
    demo.process_video(
        skip_frames=1,      # Process every frame
        max_frames=None,    # Process all frames
        display=True        # Display with annotations
    )


if __name__ == '__main__':
    main()
