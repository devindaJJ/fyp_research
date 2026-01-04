"""
Integration utilities for linking ANPR with tracked vehicles.
"""
from typing import Dict, List, Tuple, Optional


def calculate_iou(box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
    """
    Calculate Intersection over Union (IoU) between two bounding boxes.
    
    Args:
        box1: First bounding box (x1, y1, x2, y2)
        box2: Second bounding box (x1, y1, x2, y2)
        
    Returns:
        IoU score between 0 and 1
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2
    
    # Calculate intersection area
    x_left = max(x1_1, x1_2)
    y_top = max(y1_1, y1_2)
    x_right = min(x2_1, x2_2)
    y_bottom = min(y2_1, y2_2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union area
    box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
    box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
    union_area = box1_area + box2_area - intersection_area
    
    if union_area == 0:
        return 0.0
    
    return intersection_area / union_area


def is_contained(plate_box: Tuple[int, int, int, int], 
                 vehicle_box: Tuple[int, int, int, int],
                 margin: int = 0) -> bool:
    """
    Check if a plate bounding box is contained within a vehicle bounding box.
    
    Args:
        plate_box: Plate bounding box (x1, y1, x2, y2)
        vehicle_box: Vehicle bounding box (x1, y1, x2, y2)
        margin: Tolerance margin in pixels (default: 0)
        
    Returns:
        True if plate is contained within vehicle (with margin)
    """
    px1, py1, px2, py2 = plate_box
    vx1, vy1, vx2, vy2 = vehicle_box
    
    return (px1 >= vx1 - margin and 
            py1 >= vy1 - margin and 
            px2 <= vx2 + margin and 
            py2 <= vy2 + margin)


def match_plate_to_vehicle(
    plate_bbox: Tuple[int, int, int, int],
    vehicle_tracks: Dict[int, Dict],
    iou_threshold: float = 0.05,  # Lowered from 0.1 for more lenient matching
    use_containment: bool = True
) -> Optional[int]:
    """
    Match a detected plate to a tracked vehicle using IoU and/or containment.
    
    Args:
        plate_bbox: Plate bounding box (x1, y1, x2, y2)
        vehicle_tracks: Dictionary of {track_id: {'bbox': (x1,y1,x2,y2), ...}}
        iou_threshold: Minimum IoU score for matching (default: 0.1)
        use_containment: Whether to also check containment (default: True)
        
    Returns:
        track_id of best matching vehicle, or None if no match found
    """
    best_track_id = None
    best_score = 0.0
    
    for track_id, track_data in vehicle_tracks.items():
        if 'bbox' not in track_data:
            continue
        
        vehicle_bbox = track_data['bbox']
        
        # Check containment first (usually more reliable for plates)
        if use_containment and is_contained(plate_bbox, vehicle_bbox, margin=20):  # Increased margin from 10 to 20
            iou = calculate_iou(plate_bbox, vehicle_bbox)
            if iou > best_score:
                best_score = iou
                best_track_id = track_id
        else:
            # Fall back to IoU matching
            iou = calculate_iou(plate_bbox, vehicle_bbox)
            if iou >= iou_threshold and iou > best_score:
                best_score = iou
                best_track_id = track_id
    
    return best_track_id


class VehicleDataIntegrator:
    """
    Integrates vehicle tracking data with ANPR results.
    Maintains a shared structure of per-vehicle information.
    """
    
    def __init__(self, speed_limit: float = 60.0):
        """
        Initialize the integrator.
        
        Args:
            speed_limit: Speed limit in km/h for violation detection
        """
        self.vehicle_data: Dict[int, Dict] = {}
        self.speed_limit = speed_limit
    
    def update_vehicle_tracking(self, track_id: int, bbox: Tuple[int, int, int, int],
                               speed: Optional[float] = None):
        """
        Update vehicle tracking information.
        
        Args:
            track_id: Vehicle track ID
            bbox: Vehicle bounding box (x1, y1, x2, y2)
            speed: Vehicle speed in km/h (optional)
        """
        if track_id not in self.vehicle_data:
            self.vehicle_data[track_id] = {
                'track_id': track_id,
                'bbox': bbox,
                'speed': None,
                'plate': None,
                'plate_confidence': 0,
                'violation': False
            }
        
        self.vehicle_data[track_id]['bbox'] = bbox
        
        if speed is not None:
            self.vehicle_data[track_id]['speed'] = speed
            self.vehicle_data[track_id]['violation'] = speed > self.speed_limit
    
    def update_vehicle_plate(self, track_id: int, plate_text: str, confidence: float = 1.0):
        """
        Update vehicle plate information.
        
        Args:
            track_id: Vehicle track ID
            plate_text: Detected plate text
            confidence: Confidence score (for future use)
        """
        if track_id in self.vehicle_data:
            # Only update if we don't have a plate or new confidence is higher
            if (self.vehicle_data[track_id]['plate'] is None or 
                confidence > self.vehicle_data[track_id]['plate_confidence']):
                self.vehicle_data[track_id]['plate'] = plate_text
                self.vehicle_data[track_id]['plate_confidence'] = confidence
    
    def link_plates_to_vehicles(self, plates_data: List[Dict],
                               iou_threshold: float = 0.05,  # Lowered from 0.1
                               use_containment: bool = True,
                               debug: bool = False):
        """
        Link detected plates to tracked vehicles.
        
        Args:
            plates_data: List of plate detection results from ANPR
            iou_threshold: Minimum IoU for matching
            use_containment: Whether to use containment check
            debug: Print debug information
        """
        for plate_info in plates_data:
            plate_bbox = plate_info['bbox']
            plate_text = plate_info.get('text')
            
            if not plate_text:
                continue
            
            # Find matching vehicle
            track_id = match_plate_to_vehicle(
                plate_bbox,
                self.vehicle_data,
                iou_threshold,
                use_containment
            )
            
            if debug:
                print(f"[DEBUG] Plate '{plate_text}' at {plate_bbox} matched to vehicle: {track_id}")
            
            if track_id is not None:
                self.update_vehicle_plate(track_id, plate_text)
    
    def get_vehicle_data(self, track_id: int) -> Optional[Dict]:
        """
        Get data for a specific vehicle.
        
        Args:
            track_id: Vehicle track ID
            
        Returns:
            Vehicle data dictionary or None
        """
        return self.vehicle_data.get(track_id)
    
    def get_all_vehicles(self) -> Dict[int, Dict]:
        """
        Get data for all tracked vehicles.
        
        Returns:
            Dictionary of all vehicle data
        """
        return self.vehicle_data.copy()
    
    def get_violations(self) -> List[Dict]:
        """
        Get all vehicles with violations (speeding).
        
        Returns:
            List of vehicle data dictionaries with violations
        """
        return [data for data in self.vehicle_data.values() if data['violation']]
    
    def clean_old_vehicles(self, active_track_ids: List[int]):
        """
        Remove data for vehicles that are no longer being tracked.
        
        Args:
            active_track_ids: List of currently active track IDs
        """
        for track_id in list(self.vehicle_data.keys()):
            if track_id not in active_track_ids:
                del self.vehicle_data[track_id]
    
    def print_vehicle_summary(self, track_id: int):
        """
        Print a summary for a specific vehicle.
        
        Args:
            track_id: Vehicle track ID
        """
        if track_id not in self.vehicle_data:
            return
        
        data = self.vehicle_data[track_id]
        speed_str = f"{data['speed']:.1f} km/h" if data['speed'] is not None else "N/A"
        plate_str = data['plate'] if data['plate'] else "N/A"
        violation_str = "YES" if data['violation'] else "NO"
        
        print(f"Track ID: {track_id:4d} | Speed: {speed_str:12s} | Plate: {plate_str:15s} | Violation: {violation_str}")
    
    def print_all_vehicles(self):
        """
        Print summary for all vehicles.
        """
        if not self.vehicle_data:
            print("No vehicles tracked.")
            return
        
        print("\n" + "="*80)
        print("VEHICLE TRACKING SUMMARY")
        print("="*80)
        print(f"{'Track ID':<10} {'Speed (km/h)':<15} {'Number Plate':<20} {'Violation':<10}")
        print("-"*80)
        
        for track_id in sorted(self.vehicle_data.keys()):
            data = self.vehicle_data[track_id]
            speed_str = f"{data['speed']:.1f}" if data['speed'] is not None else "N/A"
            plate_str = data['plate'] if data['plate'] else "N/A"
            violation_str = "YES" if data['violation'] else "NO"
            
            print(f"{track_id:<10} {speed_str:<15} {plate_str:<20} {violation_str:<10}")
        
        print("="*80 + "\n")
