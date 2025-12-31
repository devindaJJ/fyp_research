"""
Real-time safety and incident detection system.
Detects dangerous driving behaviors, collisions, and near-miss incidents.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math


class SafetyEventDetector:
    """
    Detect dangerous driving behaviors and incidents in real-time.
    """
    
    def __init__(self):
        """Initialize safety detector."""
        self.vehicle_history = {}  # Track previous states
        self.alerts = []  # All detected alerts
        self.collisions = []  # Serious incidents
        self.near_misses = []  # Close calls
        self.behavioral_alerts = []  # Aggressive driving
    
    def update_vehicle_state(self, track_id: int, bbox: Tuple, speed: Optional[float]):
        """
        Update vehicle state for history tracking.
        
        Args:
            track_id: Vehicle track ID
            bbox: Current bounding box
            speed: Current speed in km/h
        """
        if track_id not in self.vehicle_history:
            self.vehicle_history[track_id] = {
                'prev_bbox': bbox,
                'prev_speed': speed,
                'prev_frame': 0,
                'acceleration_events': 0,
                'braking_events': 0,
                'weaving_events': 0
            }
        else:
            self.vehicle_history[track_id]['prev_bbox'] = self.vehicle_history[track_id].get('curr_bbox', bbox)
            self.vehicle_history[track_id]['prev_speed'] = self.vehicle_history[track_id].get('curr_speed', speed)
        
        self.vehicle_history[track_id]['curr_bbox'] = bbox
        self.vehicle_history[track_id]['curr_speed'] = speed
    
    def detect_sudden_acceleration(self, track_id: int, current_speed: Optional[float],
                                   time_delta: float = 0.033) -> Optional[Dict]:
        """
        Detect sudden aggressive acceleration.
        
        Args:
            track_id: Vehicle track ID
            current_speed: Current speed in km/h
            time_delta: Time between frames (seconds)
            
        Returns:
            Alert dictionary if detected, None otherwise
        """
        if track_id not in self.vehicle_history or current_speed is None:
            return None
        
        prev_speed = self.vehicle_history[track_id].get('prev_speed')
        
        if prev_speed is None:
            return None
        
        # Calculate acceleration (km/h per second)
        acceleration = (current_speed - prev_speed) / time_delta
        
        # More than 10 km/h per second = aggressive
        if acceleration > 10:
            self.vehicle_history[track_id]['acceleration_events'] += 1
            
            return {
                'type': 'AGGRESSIVE_ACCELERATION',
                'track_id': track_id,
                'severity': 'MEDIUM',
                'current_speed': current_speed,
                'acceleration': acceleration,
                'threshold': 10,
                'description': f'Acceleration: {acceleration:.1f} km/h/s (Threshold: 10)',
                'timestamp': datetime.now()
            }
        
        return None
    
    def detect_hard_braking(self, track_id: int, current_speed: Optional[float],
                           time_delta: float = 0.033) -> Optional[Dict]:
        """
        Detect sudden hard braking.
        
        Args:
            track_id: Vehicle track ID
            current_speed: Current speed in km/h
            time_delta: Time between frames
            
        Returns:
            Alert dictionary if detected
        """
        if track_id not in self.vehicle_history or current_speed is None:
            return None
        
        prev_speed = self.vehicle_history[track_id].get('prev_speed')
        
        if prev_speed is None:
            return None
        
        # Calculate deceleration (km/h per second)
        deceleration = (prev_speed - current_speed) / time_delta
        
        # More than 8 km/h deceleration per second = hard brake
        if deceleration > 8:
            self.vehicle_history[track_id]['braking_events'] += 1
            
            return {
                'type': 'HARD_BRAKING',
                'track_id': track_id,
                'severity': 'MEDIUM',
                'current_speed': current_speed,
                'deceleration': deceleration,
                'threshold': 8,
                'description': f'Hard braking: {deceleration:.1f} km/h/s (Threshold: 8)',
                'timestamp': datetime.now()
            }
        
        return None
    
    def detect_lane_weaving(self, track_id: int, bbox: Tuple[int, int, int, int]) -> Optional[Dict]:
        """
        Detect erratic/weaving movement.
        
        Args:
            track_id: Vehicle track ID
            bbox: Current bounding box (x1, y1, x2, y2)
            
        Returns:
            Alert dictionary if detected
        """
        if track_id not in self.vehicle_history:
            return None
        
        prev_bbox = self.vehicle_history[track_id].get('prev_bbox')
        
        if prev_bbox is None:
            return None
        
        # Calculate lateral movement
        curr_center_x = (bbox[0] + bbox[2]) / 2
        prev_center_x = (prev_bbox[0] + prev_bbox[2]) / 2
        
        x_shift = abs(curr_center_x - prev_center_x)
        
        # More than 40 pixels shift = weaving
        if x_shift > 40:
            self.vehicle_history[track_id]['weaving_events'] += 1
            
            return {
                'type': 'ERRATIC_MOVEMENT',
                'track_id': track_id,
                'severity': 'HIGH',
                'lateral_shift': x_shift,
                'threshold': 40,
                'description': f'Erratic movement: {x_shift:.0f}px shift (Threshold: 40px)',
                'timestamp': datetime.now()
            }
        
        return None
    
    def detect_collision(self, vehicle1: Dict, vehicle2: Dict) -> Optional[Dict]:
        """
        Detect collision between two vehicles.
        
        Args:
            vehicle1: First vehicle data
            vehicle2: Second vehicle data
            
        Returns:
            Collision alert if detected
        """
        bbox1 = vehicle1.get('bbox')
        bbox2 = vehicle2.get('bbox')
        
        if not bbox1 or not bbox2:
            return None
        
        overlap = self.calculate_bbox_overlap(bbox1, bbox2)
        
        # 50%+ overlap = collision
        if overlap > 0.5:
            return {
                'type': 'COLLISION',
                'track_ids': [vehicle1['track_id'], vehicle2['track_id']],
                'plates': [vehicle1.get('plate', 'N/A'), vehicle2.get('plate', 'N/A')],
                'severity': 'CRITICAL',
                'overlap': overlap,
                'description': f'COLLISION DETECTED: {overlap*100:.0f}% overlap',
                'timestamp': datetime.now()
            }
        
        return None
    
    def detect_near_miss(self, vehicle1: Dict, vehicle2: Dict,
                        min_distance: float = 100) -> Optional[Dict]:
        """
        Detect dangerous close proximity.
        
        Args:
            vehicle1: First vehicle data
            vehicle2: Second vehicle data
            min_distance: Minimum safe distance in pixels
            
        Returns:
            Near-miss alert if detected
        """
        bbox1 = vehicle1.get('bbox')
        bbox2 = vehicle2.get('bbox')
        speed1 = vehicle1.get('speed')
        speed2 = vehicle2.get('speed')
        
        if not bbox1 or not bbox2:
            return None
        
        distance = self.calculate_bbox_distance(bbox1, bbox2)
        
        # Close proximity + high relative speed = near miss
        if distance < min_distance:
            if speed1 and speed2:
                relative_speed = abs(speed1 - speed2)
                
                # Only alert if there's significant speed difference (not moving together)
                if relative_speed > 15:
                    return {
                        'type': 'NEAR_MISS',
                        'track_ids': [vehicle1['track_id'], vehicle2['track_id']],
                        'plates': [vehicle1.get('plate', 'N/A'), vehicle2.get('plate', 'N/A')],
                        'severity': 'HIGH',
                        'distance': distance,
                        'relative_speed': relative_speed,
                        'description': f'NEAR-MISS: {distance:.0f}px distance, {relative_speed:.0f} km/h relative speed',
                        'timestamp': datetime.now()
                    }
        
        return None
    
    @staticmethod
    def calculate_bbox_overlap(bbox1: Tuple, bbox2: Tuple) -> float:
        """
        Calculate intersection over union (IoU) between two boxes.
        
        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)
            
        Returns:
            Overlap ratio (0-1)
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Intersection
        x_left = max(x1_1, x1_2)
        y_top = max(y1_1, y1_2)
        x_right = min(x2_1, x2_2)
        y_bottom = min(y2_1, y2_2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def calculate_bbox_distance(bbox1: Tuple, bbox2: Tuple) -> float:
        """
        Calculate minimum distance between two bounding boxes.
        
        Args:
            bbox1: First bounding box (x1, y1, x2, y2)
            bbox2: Second bounding box (x1, y1, x2, y2)
            
        Returns:
            Distance in pixels
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Center points
        cx1 = (x1_1 + x2_1) / 2
        cy1 = (y1_1 + y2_1) / 2
        cx2 = (x1_2 + x2_2) / 2
        cy2 = (y1_2 + y2_2) / 2
        
        # Euclidean distance
        distance = math.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
        
        return distance
    
    def process_frame(self, vehicles: Dict) -> List[Dict]:
        """
        Process all vehicles in current frame and detect alerts.
        
        Args:
            vehicles: Dictionary of {track_id: vehicle_data}
            
        Returns:
            List of alerts detected in this frame
        """
        frame_alerts = []
        
        # Update states and check individual behaviors
        for track_id, vehicle in vehicles.items():
            bbox = vehicle.get('bbox')
            speed = vehicle.get('speed')
            
            # Update history
            self.update_vehicle_state(track_id, bbox, speed)
            
            # Check for acceleration
            accel_alert = self.detect_sudden_acceleration(track_id, speed)
            if accel_alert:
                frame_alerts.append(accel_alert)
                self.behavioral_alerts.append(accel_alert)
            
            # Check for braking
            brake_alert = self.detect_hard_braking(track_id, speed)
            if brake_alert:
                frame_alerts.append(brake_alert)
                self.behavioral_alerts.append(brake_alert)
            
            # Check for weaving
            weave_alert = self.detect_lane_weaving(track_id, bbox)
            if weave_alert:
                frame_alerts.append(weave_alert)
                self.behavioral_alerts.append(weave_alert)
        
        # Check interactions between vehicles
        vehicle_list = list(vehicles.items())
        for i in range(len(vehicle_list)):
            for j in range(i + 1, len(vehicle_list)):
                track_id1, vehicle1 = vehicle_list[i]
                track_id2, vehicle2 = vehicle_list[j]
                
                # Check for collision
                collision = self.detect_collision(vehicle1, vehicle2)
                if collision:
                    frame_alerts.append(collision)
                    self.collisions.append(collision)
                
                # Check for near-miss
                near_miss = self.detect_near_miss(vehicle1, vehicle2)
                if near_miss:
                    frame_alerts.append(near_miss)
                    self.near_misses.append(near_miss)
        
        # Store all alerts
        self.alerts.extend(frame_alerts)
        
        return frame_alerts
    
    def print_frame_alerts(self, frame_alerts: List[Dict]):
        """
        Print alerts from current frame in real-time.
        
        Args:
            frame_alerts: List of alerts from this frame
        """
        for alert in frame_alerts:
            icon = {
                'COLLISION': '🚨',
                'NEAR_MISS': '⚠️',
                'AGGRESSIVE_ACCELERATION': '⚡',
                'HARD_BRAKING': '🛑',
                'ERRATIC_MOVEMENT': '↔️'
            }.get(alert['type'], '⚠️')
            
            time_str = alert['timestamp'].strftime('%H:%M:%S')
            description = alert['description']
            
            print(f"[{time_str}] {icon} {description}")
    
    def print_summary(self):
        """Print comprehensive safety summary."""
        total_alerts = len(self.alerts)
        collisions = len(self.collisions)
        near_misses = len(self.near_misses)
        behavioral = len(self.behavioral_alerts)
        
        print("\n" + "="*80)
        print("REAL-TIME SAFETY ALERT SUMMARY")
        print("="*80)
        print(f"Total Alerts: {total_alerts}")
        print(f"  🚨 Critical (Collisions): {collisions}")
        print(f"  ⚠️  High (Near-Misses): {near_misses}")
        print(f"  ⚡ Behavioral Issues: {behavioral}")
        print("="*80)
        
        if collisions > 0:
            print("\nCRITICAL INCIDENTS:")
            for incident in self.collisions:
                plates = incident['plates']
                print(f"  - COLLISION: {plates[0]} ↔ {plates[1]}")
        
        if near_misses > 0:
            print("\nHIGH-RISK NEAR-MISSES:")
            for incident in self.near_misses[:5]:  # Show top 5
                plates = incident['plates']
                print(f"  - {plates[0]} ↔ {plates[1]} (Distance: {incident['distance']:.0f}px)")
        
        if behavioral > 0:
            print("\nBEHAVIORAL VIOLATIONS:")
            
            # Count by type
            accel_count = sum(1 for a in self.behavioral_alerts if a['type'] == 'AGGRESSIVE_ACCELERATION')
            brake_count = sum(1 for a in self.behavioral_alerts if a['type'] == 'HARD_BRAKING')
            weave_count = sum(1 for a in self.behavioral_alerts if a['type'] == 'ERRATIC_MOVEMENT')
            
            if accel_count > 0:
                print(f"  ⚡ Aggressive Accelerations: {accel_count}")
            if brake_count > 0:
                print(f"  🛑 Hard Braking Events: {brake_count}")
            if weave_count > 0:
                print(f"  ↔️  Erratic Movements: {weave_count}")
        
        print("="*80 + "\n")