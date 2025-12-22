from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Location:
    """Represents a geographic location."""
    latitude: float
    longitude: float
    address: str
    city: str
    country: str = "Sri Lanka"
    accuracy: float = 1.0
    source: str = "unknown"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_coordinates(self) -> str:
        """Return coordinates as string."""
        return f"{self.latitude},{self.longitude}"
    
    def is_in_sri_lanka(self) -> bool:
        """Check if location is within Sri Lanka."""
        sri_lanka_bounds = {
            'min_lat': 5.5, 'max_lat': 10.0,
            'min_lon': 79.5, 'max_lon': 82.0
        }
        return (
            sri_lanka_bounds['min_lat'] <= self.latitude <= sri_lanka_bounds['max_lat'] and
            sri_lanka_bounds['min_lon'] <= self.longitude <= sri_lanka_bounds['max_lon']
        )