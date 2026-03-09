"""
Lane detection and violation analysis module.
Detects lane markings, tracks lane assignments, and identifies illegal lane changes.
"""
from typing import Dict, List, Tuple, Optional
import cv2
import numpy as np
from datetime import datetime
from dataclasses import dataclass


@dataclass
class LaneInfo:
    """Information about a detected lane."""
    lane_id: int
    center_x: float
    width: float
    confidence: float
    points: List[Tuple[int, int]]


@dataclass
class VehicleLaneHistory:
    """Tracks a vehicle's lane position over time."""
    track_id: int
    current_lane_id: Optional[int] = None
    previous_lane_id: Optional[int] = None
    lane_change_count: int = 0
    lane_change_timestamps: List[datetime] = None
    center_x_history: List[float] = None
    frame_count: int = 0
    
    def __post_init__(self):
        if self.lane_change_timestamps is None:
            self.lane_change_timestamps = []
        if self.center_x_history is None:
            self.center_x_history = []


class LaneDetector:
    """
    Detect lane markings in a frame using image processing.
    Uses edge detection and Hough transform to find lane lines.
    """
    
    def __init__(self, frame_height: int = 480, frame_width: int = 640):
        """
        Initialize lane detector.
        
        Args:
            frame_height: Expected frame height in pixels
            frame_width: Expected frame width in pixels
        """
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.roi_top = int(frame_height * 0.3)  # Focus on lower portion of image
        self.roi_bottom = frame_height
        
    def detect_lane_markings(self, frame: np.ndarray) -> Tuple[List[np.ndarray], np.ndarray]:
        """
        Detect lane markings using edge detection and Hough transform.
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (detected_lines, processed_frame)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Canny edge detection
        edges = cv2.Canny(blurred, 80, 200)
        
        # ROI mask (focus on driving lane area)
        mask = np.zeros_like(edges)
        mask[self.roi_top:self.roi_bottom, :] = 1
        edges = edges * mask.astype(np.uint8)
        
        # Hough transform to detect lines
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=30,
            minLineLength=30,
            maxLineGap=10
        )
        
        # Filter lines by angle (lanes are mostly vertical)
        filtered_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                # Accept lines that are mostly vertical (70-180 degrees)
                if 70 < abs(angle) < 180 or angle == 0:
                    filtered_lines.append(line[0])
        
        return filtered_lines, edges
    
    def extract_lanes_from_lines(self, lines: List[Tuple[int, int, int, int]], 
                                frame: np.ndarray) -> List[LaneInfo]:
        """
        Group detected lines into lanes using clustering.
        
        Args:
            lines: List of detected line endpoints
            frame: Original frame for context
            
        Returns:
            List of detected lanes
        """
        if not lines:
            return []
        
        # Extract x-coordinates of line centers
        line_centers = []
        for x1, y1, x2, y2 in lines:
            center_x = (x1 + x2) / 2
            line_centers.append(center_x)
        
        # Simple clustering: group lines within 50 pixels
        lanes = []
        sorted_centers = sorted(set(line_centers))
        
        if not sorted_centers:
            return []
        
        current_cluster = [sorted_centers[0]]
        
        for center in sorted_centers[1:]:
            if center - current_cluster[-1] < 50:
                current_cluster.append(center)
            else:
                # Create lane from cluster
                lane_center = np.mean(current_cluster)
                lane_width = max(current_cluster) - min(current_cluster)
                lanes.append(LaneInfo(
                    lane_id=len(lanes),
                    center_x=lane_center,
                    width=max(lane_width, 30),
                    confidence=len(current_cluster) / len(sorted_centers),
                    points=[(int(x), 0) for x in current_cluster]
                ))
                current_cluster = [center]
        
        # Add last cluster
        if current_cluster:
            lane_center = np.mean(current_cluster)
            lane_width = max(current_cluster) - min(current_cluster) if len(current_cluster) > 1 else 30
            lanes.append(LaneInfo(
                lane_id=len(lanes),
                center_x=lane_center,
                width=max(lane_width, 30),
                confidence=len(current_cluster) / len(sorted_centers),
                points=[(int(x), 0) for x in current_cluster]
            ))
        
        return lanes


class LaneViolationDetector:
    """
    Detect lane violations such as improper lane changes and crossing.
    Tracks vehicle positions across lanes and identifies violations.
    """
    
    def __init__(self, min_frames_in_lane: int = 5, 
                 excessive_change_threshold: int = 5):
        """
        Initialize lane violation detector.
        
        Args:
            min_frames_in_lane: Minimum frames vehicle must be in a lane
            excessive_change_threshold: Number of changes to trigger violation
        """
        self.vehicle_lanes: Dict[int, VehicleLaneHistory] = {}
        self.detected_lanes: List[LaneInfo] = []
        self.min_frames_in_lane = min_frames_in_lane
        self.excessive_change_threshold = excessive_change_threshold
        self.lane_history_size = 30  # Frames to keep in history
    
    def update_lanes(self, lanes: List[LaneInfo]):
        """
        Update detected lanes.
        
        Args:
            lanes: List of LaneInfo objects from LaneDetector
        """
        self.detected_lanes = lanes
    
    def assign_lane(self, vehicle_bbox: Tuple[int, int, int, int]) -> Optional[int]:
        """
        Assign vehicle to nearest lane based on bounding box center.
        
        Args:
            vehicle_bbox: Vehicle bounding box (x1, y1, x2, y2)
            
        Returns:
            Lane ID or None if no lanes detected
        """
        if not self.detected_lanes:
            return None
        
        # Get vehicle center
        vehicle_center_x = (vehicle_bbox[0] + vehicle_bbox[2]) / 2
        
        # Find nearest lane
        nearest_lane = None
        min_distance = float('inf')
        
        for lane in self.detected_lanes:
            distance = abs(vehicle_center_x - lane.center_x)
            if distance < min_distance:
                min_distance = distance
                nearest_lane = lane
        
        # Only assign if vehicle is reasonably close to lane
        if nearest_lane and min_distance < nearest_lane.width * 2:
            return nearest_lane.lane_id
        
        return None
    
    def update_vehicle_lane(self, track_id: int, vehicle_bbox: Tuple[int, int, int, int],
                           vehicle_speed: Optional[float] = None) -> Optional[Dict]:
        """
        Update vehicle lane assignment and detect violations.
        
        Args:
            track_id: Vehicle track ID
            vehicle_bbox: Vehicle bounding box (x1, y1, x2, y2)
            vehicle_speed: Vehicle speed in km/h (optional)
            
        Returns:
            Violation dictionary if detected, None otherwise
        """
        if track_id not in self.vehicle_lanes:
            self.vehicle_lanes[track_id] = VehicleLaneHistory(track_id)
        
        history = self.vehicle_lanes[track_id]
        history.frame_count += 1
        
        # Assign lane
        current_lane = self.assign_lane(vehicle_bbox)
        vehicle_center_x = (vehicle_bbox[0] + vehicle_bbox[2]) / 2
        history.center_x_history.append(vehicle_center_x)
        
        # Keep history size limited
        if len(history.center_x_history) > self.lane_history_size:
            history.center_x_history.pop(0)
        
        # Check for lane change
        if current_lane is not None:
            if history.current_lane_id is not None and current_lane != history.current_lane_id:
                # Lane change detected
                history.previous_lane_id = history.current_lane_id
                history.current_lane_id = current_lane
                history.lane_change_count += 1
                history.lane_change_timestamps.append(datetime.now())
                
                # Check if change is abrupt/illegal
                violation = self._detect_illegal_lane_change(
                    history, current_lane, vehicle_bbox, vehicle_speed
                )
                return violation
            
            history.current_lane_id = current_lane
            
            # Check for excessive lane changes
            if len(history.lane_change_timestamps) >= self.excessive_change_threshold:
                recent_changes = sum(
                    1 for ts in history.lane_change_timestamps[-10:]
                    if (datetime.now() - ts).total_seconds() < 3  # Within 3 seconds
                )
                if recent_changes >= self.excessive_change_threshold:
                    return {
                        'type': 'EXCESSIVE_LANE_CHANGES',
                        'track_id': track_id,
                        'severity': 'HIGH',
                        'lane_change_count': len(history.lane_change_timestamps),
                        'recent_changes': recent_changes,
                        'description': f'Excessive lane changes: {recent_changes} in 3 seconds',
                        'timestamp': datetime.now()
                    }
        
        return None
    
    def _detect_illegal_lane_change(self, history: VehicleLaneHistory,
                                   target_lane_id: int,
                                   vehicle_bbox: Tuple[int, int, int, int],
                                   vehicle_speed: Optional[float]) -> Optional[Dict]:
        """
        Detect if lane change is illegal based on criteria.
        
        Args:
            history: Vehicle lane history
            target_lane_id: Target lane ID
            vehicle_bbox: Current vehicle bounding box
            vehicle_speed: Vehicle speed in km/h
            
        Returns:
            Violation dict if change is illegal, None otherwise
        """
        violation_score = 0
        violation_reasons = []
        
        # Check 1: Change too close to another vehicle (analyzed via geometry)
        if len(history.center_x_history) >= 3:
            # Calculate lateral acceleration (change in change of position)
            recent_positions = history.center_x_history[-5:]
            if len(recent_positions) >= 3:
                velocity1 = recent_positions[1] - recent_positions[0]
                velocity2 = recent_positions[2] - recent_positions[1]
                acceleration = velocity2 - velocity1
                
                if abs(acceleration) > 15:  # Abrupt change
                    violation_score += 2
                    violation_reasons.append("Abrupt lane change")
        
        # Check 2: High-speed lane change
        if vehicle_speed and vehicle_speed > 80:  # High speed
            violation_score += 1
            violation_reasons.append("Lane change at high speed")
        
        # Check 3: Rapid consecutive changes
        if history.lane_change_count >= 2:
            time_since_last = (datetime.now() - history.lane_change_timestamps[-1]).total_seconds()
            if time_since_last < 2:  # Less than 2 seconds between changes
                violation_score += 2
                violation_reasons.append("Rapid consecutive lane changes")
        
        # Generate violation if score high enough
        if violation_score >= 2:
            severity_map = {2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL'}
            severity = severity_map.get(violation_score, 'LOW')
            
            return {
                'type': 'ILLEGAL_LANE_CHANGE',
                'track_id': history.track_id,
                'severity': severity,
                'from_lane': history.previous_lane_id,
                'to_lane': target_lane_id,
                'violation_score': violation_score,
                'speed': vehicle_speed,
                'description': f"Illegal lane change: {'; '.join(violation_reasons)}",
                'timestamp': datetime.now()
            }
        
        return None
    
    def detect_lane_crossing(self, vehicle_bbox: Tuple[int, int, int, int],
                            track_id: int) -> Optional[Dict]:
        """
        Detect if vehicle is crossing lane lines inappropriately.
        
        Args:
            vehicle_bbox: Vehicle bounding box
            track_id: Vehicle track ID
            
        Returns:
            Violation dictionary if crossing detected, None otherwise
        """
        if not self.detected_lanes or track_id not in self.vehicle_lanes:
            return None
        
        history = self.vehicle_lanes[track_id]
        
        # Check if vehicle spans multiple lanes (indicator of crossing)
        vehicle_left = vehicle_bbox[0]
        vehicle_right = vehicle_bbox[2]
        
        lanes_under_vehicle = []
        for lane in self.detected_lanes:
            lane_left = lane.center_x - lane.width / 2
            lane_right = lane.center_x + lane.width / 2
            
            # Check for overlap
            overlap_left = max(vehicle_left, lane_left)
            overlap_right = min(vehicle_right, lane_right)
            
            if overlap_right > overlap_left:
                lanes_under_vehicle.append(lane.lane_id)
        
        # If spanning 2+ lanes without being in transition
        if len(lanes_under_vehicle) >= 2 and history.frame_count % 3 == 0:
            return {
                'type': 'LANE_CROSSING',
                'track_id': track_id,
                'severity': 'MEDIUM',
                'lanes_spanned': lanes_under_vehicle,
                'description': f"Vehicle spanning multiple lanes: {lanes_under_vehicle}",
                'timestamp': datetime.now()
            }
        
        return None
    
    def get_vehicle_lane_status(self, track_id: int) -> Dict:
        """
        Get current lane status for a vehicle.
        
        Args:
            track_id: Vehicle track ID
            
        Returns:
            Dictionary with lane status information
        """
        if track_id not in self.vehicle_lanes:
            return {'track_id': track_id, 'status': 'unknown'}
        
        history = self.vehicle_lanes[track_id]
        return {
            'track_id': track_id,
            'current_lane': history.current_lane_id,
            'lane_change_count': history.lane_change_count,
            'total_lanes_used': len(set([l for l in [history.current_lane_id, history.previous_lane_id] if l is not None]))
        }
    
    def cleanup_old_vehicles(self, active_track_ids: List[int]):
        """
        Remove tracking data for vehicles no longer in frame.
        
        Args:
            active_track_ids: List of currently tracked vehicle IDs
        """
        ids_to_remove = [vid for vid in self.vehicle_lanes.keys() 
                        if vid not in active_track_ids]
        for vid in ids_to_remove:
            del self.vehicle_lanes[vid]
