"""
Configuration constants for the Vehicle Speed Detection System.
"""
import os
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class VideoConfig:
    """Video input configuration."""
    path: str = "videos/speeding2.mp4"


@dataclass
class SpeedDetectionConfig:
    """Speed detection parameters."""
    distance_between_lines: float = 20.0  # Distance in meters between virtual lines
    speed_limit: int = 60  # Speed limit in km/h for violation detection
    line_a: int = 400  # First measurement line (Y-coordinate in pixels)
    line_b: int = 1800  # Second measurement line (Y-coordinate in pixels)


@dataclass
class ModelConfig:
    """Model configuration."""
    path: str = "yolov8n.pt"
    vehicle_classes: List[str] = None
    
    def __post_init__(self):
        if self.vehicle_classes is None:
            self.vehicle_classes = ["car", "motorcycle", "bus", "truck"]


@dataclass
class ANPRConfig:
    """ANPR (Number Plate Recognition) configuration."""
    model_path: str = "models/number_plate_yolo.pt"
    languages: List[str] = None
    confidence_threshold: float = 0.15  # Lowered from 0.25 for better detection
    image_size: int = 640
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ['en']


@dataclass
class TrackerConfig:
    """DeepSort tracker configuration."""
    max_age: int = 30
    n_init: int = 3


@dataclass
class DisplayConfig:
    """Display window configuration."""
    window_name: str = "Vehicle Speed Detection"
    window_width: int = 1280
    window_height: int = 720
    
@dataclass
class GoogleMapsConfig:
    """Google Maps API configuration."""
    api_key: str = os.getenv("GOOGLE_MAPS_API_KEY")
    road_location: str = "Galle Road, Colombo, Sri Lanka"  # Location of your video
    use_google_maps: bool = True  
    check_special_zones: bool = True  # Check for schools, hospitals
    cache_enabled: bool = True  # Cache API results to save calls


@dataclass
class AppConfig:
    """Main application configuration."""
    video: VideoConfig = None
    speed_detection: SpeedDetectionConfig = None
    model: ModelConfig = None
    anpr: ANPRConfig = None
    tracker: TrackerConfig = None
    display: DisplayConfig = None
    google_maps: GoogleMapsConfig = None  
    
    def __post_init__(self):
        if self.video is None:
            self.video = VideoConfig()
        if self.speed_detection is None:
            self.speed_detection = SpeedDetectionConfig()
        if self.model is None:
            self.model = ModelConfig()
        if self.anpr is None:
            self.anpr = ANPRConfig()
        if self.tracker is None:
            self.tracker = TrackerConfig()
        if self.display is None:
            self.display = DisplayConfig()
        if self.google_maps is None:  # ADD THIS
            self.google_maps = GoogleMapsConfig()


# Default configuration instance
config = AppConfig()