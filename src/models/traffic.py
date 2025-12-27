"""
Traffic Data Models for Urban Traffic System
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class TrafficLevel(Enum):
    """
    Enum representing different levels of traffic congestion.
    
    Levels are based on delay compared to normal travel time:
    - LIGHT: ≤5 minutes delay
    - MODERATE: 6-15 minutes delay  
    - HEAVY: 16-30 minutes delay
    - SEVERE: >30 minutes delay
    """
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"
    SEVERE = "severe"
    UNKNOWN = "unknown"
    
    def get_emoji(self) -> str:
        """
        Get emoji representation of traffic level.
        
        Returns:
            Emoji string representing traffic level
        """
        emoji_map = {
            TrafficLevel.LIGHT: "🟢",
            TrafficLevel.MODERATE: "🟡",
            TrafficLevel.HEAVY: "🟠",
            TrafficLevel.SEVERE: "🔴",
            TrafficLevel.UNKNOWN: "⚪"
        }
        return emoji_map.get(self, "⚪")
    
    def get_color_code(self) -> str:
        """
        Get color code for traffic level (for terminal output).
        
        Returns:
            Color code string
        """
        color_map = {
            TrafficLevel.LIGHT: "green",
            TrafficLevel.MODERATE: "yellow",
            TrafficLevel.HEAVY: "orange",
            TrafficLevel.SEVERE: "red",
            TrafficLevel.UNKNOWN: "white"
        }
        return color_map.get(self, "white")
    
    def get_description(self) -> str:
        """
        Get human-readable description of traffic level.
        
        Returns:
            Description string
        """
        description_map = {
            TrafficLevel.LIGHT: "Light Traffic - Smooth flow",
            TrafficLevel.MODERATE: "Moderate Traffic - Some delays",
            TrafficLevel.HEAVY: "Heavy Traffic - Significant delays",
            TrafficLevel.SEVERE: "Severe Traffic - Major congestion",
            TrafficLevel.UNKNOWN: "Traffic conditions unknown"
        }
        return description_map.get(self, "Unknown conditions")
    
    @classmethod
    def from_delay_minutes(cls, delay_minutes: float) -> 'TrafficLevel':
        """
        Determine traffic level based on delay in minutes.
        
        Args:
            delay_minutes: Delay compared to normal travel time
            
        Returns:
            TrafficLevel enum value
        """
        if delay_minutes <= 5:
            return cls.LIGHT
        elif delay_minutes <= 15:
            return cls.MODERATE
        elif delay_minutes <= 30:
            return cls.HEAVY
        else:
            return cls.SEVERE
    
    def is_heavy_or_worse(self) -> bool:
        """
        Check if traffic level is heavy or severe.
        
        Returns:
            True if traffic is heavy or severe
        """
        return self in [TrafficLevel.HEAVY, TrafficLevel.SEVERE]
    
    def should_reroute(self) -> bool:
        """
        Check if traffic level warrants rerouting.
        
        Returns:
            True if rerouting is recommended
        """
        return self.is_heavy_or_worse()


class IncidentType(Enum):
    """
    Enum representing types of traffic incidents.
    """
    ACCIDENT = "accident"
    CONSTRUCTION = "construction"
    ROAD_CLOSURE = "road_closure"
    HAZARD = "hazard"
    CONGESTION = "congestion"
    POLICE_ACTIVITY = "police_activity"
    WEATHER = "weather"
    OTHER = "other"


class IncidentSeverity(Enum):
    """
    Enum representing severity of traffic incidents.
    """
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class TrafficIncident:
    """
    Data class representing a traffic incident.
    
    Attributes:
        incident_id: Unique identifier for the incident
        type: Type of incident (accident, construction, etc.)
        description: Human-readable description
        severity: Severity level
        latitude: Geographic latitude
        longitude: Geographic longitude
        start_time: When the incident started
        end_time: Estimated end time (optional)
        delay_minutes: Estimated delay caused (optional)
        affected_roads: List of affected road names
        source: Source of the incident report
        confidence: Confidence score (0.0 to 1.0)
        reported_at: When the incident was reported
        updated_at: Last update time
    """
    incident_id: str
    type: IncidentType
    description: str
    severity: IncidentSeverity
    latitude: float
    longitude: float
    start_time: datetime
    end_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    affected_roads: List[str] = field(default_factory=list)
    source: str = "unknown"
    confidence: float = 0.8
    reported_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation."""
        # Ensure coordinates are valid
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise ValueError(f"Invalid coordinates: {self.latitude}, {self.longitude}")
        
        # Ensure confidence is in valid range
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def is_active(self) -> bool:
        """
        Check if the incident is currently active.
        
        Returns:
            True if incident is active
        """
        now = datetime.now()
        
        if self.end_time and now > self.end_time:
            return False
        
        return now >= self.start_time
    
    def get_estimated_remaining_time(self) -> Optional[float]:
        """
        Get estimated remaining time for incident resolution.
        
        Returns:
            Remaining time in minutes, or None if unknown
        """
        if not self.end_time:
            return None
        
        now = datetime.now()
        if now >= self.end_time:
            return 0.0
        
        remaining = (self.end_time - now).total_seconds() / 60
        return max(0.0, remaining)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert incident to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "incident_id": self.incident_id,
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity.value,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "delay_minutes": self.delay_minutes,
            "affected_roads": self.affected_roads,
            "source": self.source,
            "confidence": self.confidence,
            "reported_at": self.reported_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active()
        }


@dataclass
class TrafficSnapshot:
    """
    Data class representing a snapshot of traffic conditions at a location.
    
    Attributes:
        location_id: Unique identifier for the location
        latitude: Geographic latitude
        longitude: Geographic longitude
        current_speed: Current traffic speed (km/h)
        free_flow_speed: Free flow speed (km/h)
        confidence: Confidence in the data (0.0 to 1.0)
        traffic_level: Traffic congestion level
        incidents: List of active incidents at this location
        timestamp: When this snapshot was taken
        source: Source of the traffic data
        road_name: Name of the road (optional)
        road_type: Type of road (highway, arterial, etc.)
    """
    location_id: str
    latitude: float
    longitude: float
    current_speed: float
    free_flow_speed: float
    confidence: float
    traffic_level: TrafficLevel
    incidents: List[TrafficIncident] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    road_name: Optional[str] = None
    road_type: str = "unknown"
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.current_speed < 0:
            raise ValueError(f"Current speed cannot be negative: {self.current_speed}")
        if self.free_flow_speed <= 0:
            raise ValueError(f"Free flow speed must be positive: {self.free_flow_speed}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    @property
    def congestion_percentage(self) -> float:
        """
        Calculate congestion as percentage of free flow.
        
        Returns:
            Congestion percentage (0-100)
        """
        if self.free_flow_speed == 0:
            return 100.0
        
        # Congestion = reduction in speed as percentage of free flow
        congestion = ((self.free_flow_speed - self.current_speed) / self.free_flow_speed) * 100
        return max(0.0, min(100.0, congestion))
    
    @property
    def delay_factor(self) -> float:
        """
        Calculate delay factor (how much slower than free flow).
        
        Returns:
            Delay factor (1.0 = free flow, 2.0 = twice as slow)
        """
        if self.current_speed == 0:
            return float('inf')
        
        return self.free_flow_speed / max(0.1, self.current_speed)
    
    def has_incidents(self) -> bool:
        """
        Check if there are any active incidents.
        
        Returns:
            True if there are active incidents
        """
        return any(incident.is_active() for incident in self.incidents)
    
    def get_active_incidents(self) -> List[TrafficIncident]:
        """
        Get list of active incidents.
        
        Returns:
            List of active TrafficIncident objects
        """
        return [incident for incident in self.incidents if incident.is_active()]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert snapshot to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "location_id": self.location_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current_speed": self.current_speed,
            "free_flow_speed": self.free_flow_speed,
            "congestion_percentage": self.congestion_percentage,
            "delay_factor": self.delay_factor,
            "confidence": self.confidence,
            "traffic_level": self.traffic_level.value,
            "traffic_level_emoji": self.traffic_level.get_emoji(),
            "traffic_level_description": self.traffic_level.get_description(),
            "incident_count": len(self.incidents),
            "active_incident_count": len(self.get_active_incidents()),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "road_name": self.road_name,
            "road_type": self.road_type,
            "has_incidents": self.has_incidents()
        }


@dataclass
class TrafficPattern:
    """
    Data class representing traffic patterns over time.
    
    Attributes:
        location_id: Unique identifier for the location
        day_of_week: Day of week (0=Monday, 6=Sunday)
        hour_of_day: Hour of day (0-23)
        average_speed: Average speed at this time
        typical_delay: Typical delay in minutes
        confidence: Confidence in the pattern (0.0 to 1.0)
        sample_size: Number of samples used
        last_updated: When this pattern was last updated
    """
    location_id: str
    day_of_week: int  # 0=Monday, 6=Sunday
    hour_of_day: int  # 0-23
    average_speed: float
    typical_delay: float
    confidence: float
    sample_size: int
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not (0 <= self.day_of_week <= 6):
            raise ValueError(f"Day of week must be 0-6, got {self.day_of_week}")
        if not (0 <= self.hour_of_day <= 23):
            raise ValueError(f"Hour of day must be 0-23, got {self.hour_of_day}")
        if self.average_speed < 0:
            raise ValueError(f"Average speed cannot be negative: {self.average_speed}")
        if self.typical_delay < 0:
            raise ValueError(f"Typical delay cannot be negative: {self.typical_delay}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        if self.sample_size < 0:
            raise ValueError(f"Sample size cannot be negative: {self.sample_size}")
    
    def is_peak_hour(self) -> bool:
        """
        Check if this is a peak traffic hour in Sri Lanka.
        
        Returns:
            True if this is a peak hour
        """
        # Sri Lanka typical peak hours: 7-9 AM and 4-7 PM
        morning_peak = 7 <= self.hour_of_day <= 9
        evening_peak = 16 <= self.hour_of_day <= 19
        
        return morning_peak or evening_peak
    
    def get_expected_traffic_level(self) -> TrafficLevel:
        """
        Get expected traffic level based on historical patterns.
        
        Returns:
            Expected TrafficLevel
        """
        return TrafficLevel.from_delay_minutes(self.typical_delay)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pattern to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "location_id": self.location_id,
            "day_of_week": self.day_of_week,
            "hour_of_day": self.hour_of_day,
            "average_speed": self.average_speed,
            "typical_delay": self.typical_delay,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "is_peak_hour": self.is_peak_hour(),
            "expected_traffic_level": self.get_expected_traffic_level().value,
            "last_updated": self.last_updated.isoformat()
        }


# Helper functions
def create_traffic_incident(
    incident_type: str,
    description: str,
    severity: str,
    lat: float,
    lon: float,
    **kwargs
) -> TrafficIncident:
    """
    Helper function to create a TrafficIncident.
    
    Args:
        incident_type: Type of incident (accident, construction, etc.)
        description: Human-readable description
        severity: Severity level (minor, moderate, major, critical)
        lat: Latitude
        lon: Longitude
        **kwargs: Additional arguments for TrafficIncident
    
    Returns:
        TrafficIncident object
    """
    try:
        incident_type_enum = IncidentType(incident_type.lower())
    except ValueError:
        incident_type_enum = IncidentType.OTHER
    
    try:
        severity_enum = IncidentSeverity(severity.lower())
    except ValueError:
        severity_enum = IncidentSeverity.MODERATE
    
    # Generate a simple ID if not provided
    if 'incident_id' not in kwargs:
        from hashlib import md5
        from time import time
        unique_id = f"{incident_type}_{lat}_{lon}_{time()}"
        kwargs['incident_id'] = md5(unique_id.encode()).hexdigest()[:12]
    
    if 'start_time' not in kwargs:
        kwargs['start_time'] = datetime.now()
    
    return TrafficIncident(
        type=incident_type_enum,
        description=description,
        severity=severity_enum,
        latitude=lat,
        longitude=lon,
        **kwargs
    )


def calculate_traffic_level_from_speeds(
    current_speed: float,
    free_flow_speed: float
) -> TrafficLevel:
    """
    Calculate traffic level from speed data.
    
    Args:
        current_speed: Current traffic speed (km/h)
        free_flow_speed: Free flow speed (km/h)
    
    Returns:
        TrafficLevel enum value
    """
    if free_flow_speed <= 0 or current_speed < 0:
        return TrafficLevel.UNKNOWN
    
    # Calculate delay factor
    if current_speed == 0:
        delay_factor = float('inf')
    else:
        delay_factor = free_flow_speed / current_speed
    
    # Convert delay factor to approximate delay minutes
    # This is a rough estimation - in reality you'd need distance data
    estimated_delay = (delay_factor - 1) * 20  # Rough approximation
    
    return TrafficLevel.from_delay_minutes(estimated_delay)


def validate_traffic_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate traffic data dictionary.
    
    Args:
        data: Dictionary containing traffic data
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required fields
    required_fields = ['latitude', 'longitude', 'current_speed', 'free_flow_speed']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate coordinates
    if 'latitude' in data and 'longitude' in data:
        lat = data['latitude']
        lon = data['longitude']
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            errors.append("Latitude and longitude must be numbers")
        elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
            errors.append(f"Invalid coordinates: {lat}, {lon}")
    
    # Validate speeds
    if 'current_speed' in data:
        speed = data['current_speed']
        if not isinstance(speed, (int, float)):
            errors.append("Current speed must be a number")
        elif speed < 0:
            errors.append(f"Current speed cannot be negative: {speed}")
    
    if 'free_flow_speed' in data:
        speed = data['free_flow_speed']
        if not isinstance(speed, (int, float)):
            errors.append("Free flow speed must be a number")
        elif speed <= 0:
            errors.append(f"Free flow speed must be positive: {speed}")
    
    return len(errors) == 0, errors