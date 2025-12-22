import googlemaps
from typing import List, Dict, Optional, Union
from datetime import datetime
import time
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class GoogleMapsClient:
    """Enhanced Google Maps API client with rate limiting and error handling."""
    
    def __init__(self, api_key: str):
        self.client = googlemaps.Client(key=api_key)
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def get_route_alternatives(
        self,
        origin: str,
        destination: str,
        alternatives_count: int = 3,
        departure_time: Union[str, datetime] = "now",
        traffic_model: str = "best_guess"
    ) -> Optional[List[Dict]]:
        """Get multiple route alternatives with traffic information."""
        self._rate_limit()
        
        try:
            directions = self.client.directions(
                origin=origin,
                destination=destination,
                mode="driving",
                departure_time=departure_time,
                traffic_model=traffic_model,
                alternatives=True
            )
            
            # Return requested number of alternatives (or all available)
            return directions[:alternatives_count]
            
        except Exception as e:
            logger.error(f"Google Maps API error: {e}")
            return None
    
    def geocode(self, address: str) -> Optional[Dict]:
        """Geocode an address with rate limiting."""
        self._rate_limit()
        
        try:
            results = self.client.geocode(address)
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Geocoding error for {address}: {e}")
            return None
    
    def _rate_limit(self):
        """Implement rate limiting between API calls."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()