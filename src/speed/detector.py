import cv2
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from src.core.config import config


class VehicleSpeedDetector:
    """
    Class-based vehicle speed detection system using YOLO and DeepSort.
    """
    
    def __init__(self, video_path=None, distance_between_lines=None, speed_limit=None, 
                 line_a=None, line_b=None, model_path=None):
        """
        Initialize the vehicle speed detector.
        
        Args:
            video_path: Path to the video file (defaults to config)
            distance_between_lines: Distance in meters between the two virtual lines
            speed_limit: Speed limit in km/h for violation detection
            line_a: Y-coordinate of the first virtual line (pixels)
            line_b: Y-coordinate of the second virtual line (pixels)
            model_path: Path to the YOLO model
        """
        # Configuration with defaults from config file
        self.video_path = video_path or config.video.path
        self.distance_between_lines = distance_between_lines or config.speed_detection.distance_between_lines
        self.speed_limit = speed_limit or config.speed_detection.speed_limit
        self.line_a = line_a or config.speed_detection.line_a
        self.line_b = line_b or config.speed_detection.line_b
        self.vehicle_classes = config.model.vehicle_classes
        
        # Load models
        self.model = YOLO(model_path or config.model.path)
        self.tracker = DeepSort(max_age=config.tracker.max_age, n_init=config.tracker.n_init)
        
        # Vehicle tracking data
        self.vehicle_data = {}  # {track_id: {'t1': None, 't2': None, 'speed_done': False}}
        
        # Video capture
        self.cap = cv2.VideoCapture(self.video_path)
        
        # Window setup
        self.window_name = config.display.window_name
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, config.display.window_width, config.display.window_height)
    
    def detect_vehicles(self, frame):
        """
        Detect vehicles in the frame using YOLO.
        
        Args:
            frame: Input video frame
            
        Returns:
            List of detections in format [[x1, y1, x2, y2], confidence]
        """
        results = self.model(frame, verbose=False)
        detections = []
        
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = self.model.names[cls_id]
                
                if cls_name in self.vehicle_classes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    detections.append([[x1, y1, x2, y2], conf])
        
        return detections
    
    def calculate_speed(self, track_id):
        """
        Calculate vehicle speed based on crossing times.
        
        Args:
            track_id: ID of the tracked vehicle
            
        Returns:
            Speed in km/h if calculation is successful, None otherwise
        """
        if (self.vehicle_data[track_id]["t1"] and 
            self.vehicle_data[track_id]["t2"] and 
            not self.vehicle_data[track_id]["speed_done"]):
            
            t1 = self.vehicle_data[track_id]["t1"]
            t2 = self.vehicle_data[track_id]["t2"]
            
            speed_mps = self.distance_between_lines / (t2 - t1)
            speed_kmh = speed_mps * 3.6
            
            self.vehicle_data[track_id]["speed"] = speed_kmh
            self.vehicle_data[track_id]["speed_done"] = True
            
            return speed_kmh
        
        return None
    
    def process_tracks(self, tracks, frame):
        """
        Process tracked vehicles and update their data.
        
        Args:
            tracks: List of tracks from DeepSort
            frame: Current video frame
            
        Returns:
            List of active track IDs
        """
        active_ids = []
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            active_ids.append(track_id)
            
            x1, y1, x2, y2 = map(int, track.to_ltrb())
            center_y = (y1 + y2) // 2
            
            # Initialize vehicle
            if track_id not in self.vehicle_data:
                self.vehicle_data[track_id] = {"t1": None, "t2": None, "speed_done": False}
            
            # Line A crossing
            if self.vehicle_data[track_id]["t1"] is None and center_y > self.line_a:
                self.vehicle_data[track_id]["t1"] = cv2.getTickCount() / cv2.getTickFrequency()
            
            # Line B crossing
            elif self.vehicle_data[track_id]["t2"] is None and center_y > self.line_b:
                self.vehicle_data[track_id]["t2"] = cv2.getTickCount() / cv2.getTickFrequency()
            
            # Speed calculation
            self.calculate_speed(track_id)
            
            # Draw tracking information
            self.draw_track(frame, track_id, x1, y1, x2, y2)
        
        return active_ids
    
    def draw_track(self, frame, track_id, x1, y1, x2, y2):
        """
        Draw bounding box and speed information for a tracked vehicle.
        
        Args:
            frame: Current video frame
            track_id: ID of the tracked vehicle
            x1, y1, x2, y2: Bounding box coordinates
        """
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID {track_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if "speed" in self.vehicle_data[track_id]:
            speed = self.vehicle_data[track_id]["speed"]
            cv2.putText(frame, f"{int(speed)} km/h", (x1, y2 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            if speed > self.speed_limit:
                cv2.putText(frame, "SPEEDING!", (x1, y1 - 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    def draw_virtual_lines(self, frame):
        """
        Draw the virtual lines for speed measurement.
        
        Args:
            frame: Current video frame
        """
        cv2.line(frame, (0, self.line_a), (frame.shape[1], self.line_a), (255, 0, 0), 2)
        cv2.line(frame, (0, self.line_b), (frame.shape[1], self.line_b), (0, 0, 255), 2)
    
    def clean_old_tracks(self, active_ids):
        """
        Remove data for vehicles that are no longer being tracked.
        
        Args:
            active_ids: List of currently active track IDs
        """
        for vid in list(self.vehicle_data.keys()):
            if vid not in active_ids:
                del self.vehicle_data[vid]
    
    def run(self):
        """
        Main loop to process video and detect vehicle speeds.
        """
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
           
            detections = self.detect_vehicles(frame)
            tracks = self.tracker.update_tracks(detections, frame=frame)
            active_ids = self.process_tracks(tracks, frame)
            self.draw_virtual_lines(frame)
            self.clean_old_tracks(active_ids)
            
            # Display frame
            cv2.imshow(self.window_name, frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        
        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()