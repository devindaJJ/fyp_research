from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from .traffic import TrafficLevel


@dataclass
class RouteStep:
    """Represents a step in a route."""
    instruction: str
    distance_text: str
    distance_meters: int
    duration_text: str
    duration_seconds: int
    polyline: str = ""
    
    
@dataclass
class Route:
    """Represents a travel route with traffic information."""
    origin: str
    destination: str
    normal_duration: float  # minutes
    traffic_duration: float  # minutes
    delay_minutes: float
    distance_meters: int
    distance_text: str
    traffic_level: TrafficLevel
    summary: str
    steps: List[RouteStep]
    polyline: str
    is_primary: bool = False
    confidence: float = 0.8
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization to ensure numerical types."""
    
        if isinstance(self.normal_duration, str):
            try:
                self.normal_duration = float(self.normal_duration)
            except ValueError:
                self.normal_duration = 0.0
        
        if isinstance(self.traffic_duration, str):
            try:
                self.traffic_duration = float(self.traffic_duration)
            except ValueError:
                self.traffic_duration = self.normal_duration
        
        if isinstance(self.delay_minutes, str):
            try:
                self.delay_minutes = float(self.delay_minutes)
            except ValueError:
                self.delay_minutes = 0.0
        
        if isinstance(self.distance_meters, str):
            try:
                self.distance_meters = float(self.distance_meters)
            except ValueError:
                self.distance_meters = 0.0
    
    
    @property
    def delay_percentage(self) -> float:
        """Calculate delay as percentage of normal time."""
        if self.normal_duration > 0:
            return (self.delay_minutes / self.normal_duration) * 100
        return 0.0


@dataclass
class RouteAlternative(Route):
    """Represents an alternative route."""
    advantage_score: float = 0.0  
    disadvantage_reasons: List[str] = field(default_factory=list)
    
    def is_recommended(self, threshold: float = 0.6) -> bool:
        """Check if this alternative is recommended."""
        return self.advantage_score >= threshold