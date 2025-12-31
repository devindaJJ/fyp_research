import argparse
import cv2
from typing import Optional, List, Dict

from src.core.config import config
from src.speed.detector import VehicleSpeedDetector
from src.anpr.detector import NumberPlateDetector
from src.utils.integration import VehicleDataIntegrator
from src.utils.exporter import ResultExporter
from src.utils.google_maps_integration import GoogleMapsRoadContext
from src.utils.safety_detector import SafetyEventDetector


class TrafficApp:
    """
    Class-based orchestrator for speed detection, ANPR, or both.
    Keeps main.py small, clear, and extensible.
    """

    def __init__(
        self,
        mode: str,
        video_path: Optional[str] = None,
        image_path: Optional[str] = None,
        anpr_model: Optional[str] = None,
    ):
        self.mode = mode
        self.video_path = video_path
        self.image_path = image_path
        self.anpr_model = anpr_model
        self.google_maps_context = None
        self.dynamic_speed_limit = None

        self.speed_detector: Optional[VehicleSpeedDetector] = None
        self.anpr_detector: Optional[NumberPlateDetector] = None
        self.integrator: Optional[VehicleDataIntegrator] = None
        self.exporter: ResultExporter = ResultExporter()

    @staticmethod
    def parse_args():
        parser = argparse.ArgumentParser(description="Urban Traffic System Runner")
        parser.add_argument("--mode", choices=["speed", "anpr", "both"], default="speed",
                            help="Which pipeline to run")
        parser.add_argument("--video", type=str, default=None, help="Path to video file")
        parser.add_argument("--image", type=str, default=None, help="Path to image (ANPR only)")
        parser.add_argument("--anpr-model", type=str, default=None, help="Path to ANPR YOLO model")
        return parser.parse_args()

    def create_anpr_detector(self) -> NumberPlateDetector:
        model_path = (
            self.anpr_model
            or (getattr(config, "anpr").model_path if hasattr(config, "anpr") else None)
            or "models/number_plate_yolo.pt"
        )
        languages = (getattr(config, "anpr").languages if hasattr(config, "anpr") else ["en"])
        conf = (getattr(config, "anpr").confidence_threshold if hasattr(config, "anpr") else 0.25)
        img_size = (getattr(config, "anpr").image_size if hasattr(config, "anpr") else 640)
        return NumberPlateDetector(model_path=model_path, languages=languages,
                                   confidence_threshold=conf, image_size=img_size)

    def run(self):
        if self.mode == "speed":
            self.run_speed()
        elif self.mode == "anpr":
            self.run_anpr()
        else:
            self.run_both()

    def run_speed(self):
        """Run speed detection using the detector’s own loop."""
        self.speed_detector = VehicleSpeedDetector(video_path=self.video_path)
        self.speed_detector.run()

    def run_anpr(self):
        """Run ANPR on either an image or a video."""
        self.anpr_detector = self.create_anpr_detector()

        # Image mode
        if self.image_path:
            img = cv2.imread(self.image_path)
            if img is None:
                print(f"Error: could not load image: {self.image_path}")
                return
            plates = self.anpr_detector.detect_and_read(img, draw_results=True)
            if isinstance(plates, tuple):
                plates_data, annotated = plates
            else:
                plates_data, annotated = plates, img
            print(f"Detected {len(plates_data)} plate(s)")
            for p in plates_data:
                print(f"- {p['text']} (valid={p['valid']}) bbox={p['bbox']}")
            cv2.imshow("ANPR", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            return

        # Video mode
        path = self.video_path or config.video.path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"Error: could not open video: {path}")
            return

        window_name = "ANPR"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                plates = self.anpr_detector.detect_and_read(frame, draw_results=True)
                if isinstance(plates, tuple):
                    _, annotated = plates
                else:
                    annotated = frame

                cv2.imshow(window_name, annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def draw_anpr_overlays_on_frame(self, frame):
        """Run ANPR on a frame and draw overlays onto the same frame."""
        if self.anpr_detector is None:
            self.anpr_detector = self.create_anpr_detector()

        plates_data = self.anpr_detector.detect_and_read(frame, draw_results=False)
        for p in plates_data:
            (x1, y1, x2, y2) = p["bbox"]
            color = (0, 255, 0) if p["text"] else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            if p["text"]:
                cv2.putText(frame, p["text"], (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        return frame
    
    def draw_integrated_results(self, frame):
        """Draw integrated vehicle tracking and plate information on frame."""
        if self.integrator is None:
            return
        
        all_vehicles = self.integrator.get_all_vehicles()
        
        for track_id, vehicle_data in all_vehicles.items():
            bbox = vehicle_data['bbox']
            if bbox is None:
                continue
            
            x1, y1, x2, y2 = bbox
            speed = vehicle_data['speed']
            plate = vehicle_data['plate']
            violation = vehicle_data['violation']
            
            # Draw bounding box (green for normal, red for violation)
            color = (0, 0, 255) if violation else (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw track ID
            cv2.putText(frame, f"ID {track_id}", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # Draw speed
            if speed is not None:
                speed_text = f"{int(speed)} km/h"
                cv2.putText(frame, speed_text, (x1, y2 + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                if violation:
                    cv2.putText(frame, "SPEEDING!", (x1, y1 - 35),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            if plate:
                plate_color = (0, 255, 255) 
                cv2.putText(frame, plate, (x1, y2 + 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, plate_color, 2)
    def draw_safety_alerts_on_frame(self, frame, alerts: List[Dict]):
        """
        Draw safety alerts on the video frame.
        
        Args:
            frame: Video frame
            alerts: List of safety alerts from current frame
        """
        for alert in alerts:
            alert_type = alert['type']
            
            # Choose color and text based on severity
            if alert_type == 'COLLISION':
                color = (0, 0, 255)  # Red
                text = "COLLISION!"
                y_offset = 100
            elif alert_type == 'NEAR_MISS':
                color = (0, 165, 255)  # Orange
                text = "NEAR-MISS!"
                y_offset = 130
            elif alert_type == 'AGGRESSIVE_ACCELERATION':
                color = (0, 255, 255)  # Yellow
                text = "AGGRESSIVE ACCEL"
                y_offset = 160
            elif alert_type == 'HARD_BRAKING':
                color = (0, 255, 165)  # Lime
                text = "HARD BRAKE"
                y_offset = 190
            elif alert_type == 'ERRATIC_MOVEMENT':
                color = (0, 191, 255)  # Deep Sky Blue
                text = "ERRATIC MOVEMENT"
                y_offset = 220
            else:
                continue
            
            cv2.rectangle(frame, (10, y_offset - 25), (300, y_offset + 10), color, -1)
            cv2.putText(
                frame,
                text,
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

    def run_both(self):
        """Run speed detection, ANPR, and safety detection with full integration."""
    
        self.speed_detector = VehicleSpeedDetector(video_path=self.video_path)
        if self.speed_detector.cap and self.speed_detector.cap.isOpened():
            self.speed_detector.cap.release()

        self.anpr_detector = self.create_anpr_detector()
        safety_detector = SafetyEventDetector()
        
        if config.google_maps.use_google_maps and config.google_maps.api_key:
            try:
                from src.utils.google_maps_integration import GoogleMapsRoadContext
                self.google_maps_context = GoogleMapsRoadContext(config.google_maps.api_key)
                road_context = self.google_maps_context.get_complete_road_context(
                    config.google_maps.road_location
                )
                
                if road_context and 'final_speed_limit' in road_context:
                    self.dynamic_speed_limit = road_context['final_speed_limit']
                    self.speed_detector.speed_limit = self.dynamic_speed_limit
                    print(f"✓ Using Google Maps speed limit: {self.dynamic_speed_limit} KPH\n")
                
            except Exception as e:
                print(f"Google Maps integration skipped: {e}\n")
        
        speed_limit = self.speed_detector.speed_limit
        self.integrator = VehicleDataIntegrator(speed_limit=speed_limit)

        path = self.video_path or config.video.path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            print(f"Error: could not open video: {path}")
            return

        window_name = self.speed_detector.window_name
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, config.display.window_width, config.display.window_height)
        
        frame_count = 0
        print_interval = 30  

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1

                detections = self.speed_detector.detect_vehicles(frame)
                tracks = self.speed_detector.tracker.update_tracks(detections, frame=frame)
                active_ids = self.speed_detector.process_tracks(tracks, frame)
                self.speed_detector.draw_virtual_lines(frame)
                self.speed_detector.clean_old_tracks(active_ids)
                current_tracks = self.speed_detector.get_current_tracks()
                
                for track_id, track_data in current_tracks.items():
                    self.integrator.update_vehicle_tracking(
                        track_id=track_id,
                        bbox=track_data['bbox'],
                        speed=track_data['speed']
                    )
                
                plates_data = self.anpr_detector.detect_and_read(frame, draw_results=False)
                
                self.integrator.link_plates_to_vehicles(plates_data)
                self.integrator.clean_old_vehicles(active_ids)
                
                all_vehicles = self.integrator.get_all_vehicles()
                safety_alerts = safety_detector.process_frame(all_vehicles)
                
                if safety_alerts:
                    print(f"\n[Frame {frame_count}] SAFETY ALERTS DETECTED:")
                    safety_detector.print_frame_alerts(safety_alerts)
                
                self.draw_integrated_results(frame)                
                self.draw_safety_alerts_on_frame(frame, safety_alerts)
                
                if frame_count % print_interval == 0:
                    print(f"\n--- Frame {frame_count} Summary ---")
                    self.integrator.print_all_vehicles()

                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break   
        finally:
            print("\n" + "="*80)
            print("FINAL ANALYSIS COMPLETE")
            print("="*80)
            
            all_vehicles = self.integrator.get_all_vehicles()
            self.integrator.print_all_vehicles()
            safety_detector.print_summary()
            
            if all_vehicles:
                csv_path = self.exporter.export_to_csv(all_vehicles)
                json_path = self.exporter.export_to_json(all_vehicles)
                violations_path = self.exporter.export_violations_only(all_vehicles)
                
                print(f"\nResults exported to:")
                print(f"  - CSV: {csv_path}")
                print(f"  - JSON: {json_path}")
                print(f"  - Violations: {violations_path}")
                
                self.exporter.print_summary_report(all_vehicles)
            
            cap.release()
            cv2.destroyAllWindows()


def main():
    args = TrafficApp.parse_args()
    app = TrafficApp(
        mode=args.mode,
        video_path=args.video,
        image_path=args.image,
        anpr_model=args.anpr_model,
    )
    app.run_both()


if __name__ == "__main__":
    main()