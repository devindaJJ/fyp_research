from datetime import datetime
import time

class HistoricalAnalyzer:
    def __init__(self, api_key: str):
        try:
            import googlemaps
            self.gmaps = googlemaps.Client(key=api_key)
        except Exception:
            self.gmaps = None
            print("googlemaps not available; historical analysis will be disabled.")
    
    def get_historical_point(self, origin: str, destination: str, target_time: datetime):
        """
        Get historical travel time between two points at a specific time
        
        """
        try:
            """
             For historical analysis, we use standard directions without traffic 
             because Google doesn't provide historical traffic data
             """
            
            result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode="driving",
                departure_time="now",  # Use current time for API request
                alternatives=False,
                optimize_waypoints=False
            )
            
            if result and len(result) > 0:
                # Get typical duration (without historical traffic)
                duration_seconds = result[0]['legs'][0]['duration']['value']
                duration_minutes = duration_seconds / 60
                
                # Apply time-based adjustment factor (simulated)
                # This is where you'd apply your historical patterns
                hour = target_time.hour
                adjustment_factor = self._get_time_adjustment_factor(hour)
                adjusted_minutes = duration_minutes * adjustment_factor
                
                return round(adjusted_minutes, 1)
            else:
                print(f"No route found between {origin} and {destination}")
                return None
                
        except googlemaps.exceptions.HTTPError as e:
            if e.status_code == 400:
                print(f"HTTP 400 Error: Bad request - check your parameters")
            else:
                print(f"HTTP Error {e.status_code}: {e}")
            return None
        except Exception as e:
            print(f"Error in get_historical_point: {e}")
            return None
    
    def _get_time_adjustment_factor(self, hour: int) -> float:
        """
        Simulate historical traffic patterns based on time of day
        This is a simplified version - you should build this from real data
        """
        # Peak hours (8-10 AM, 5-7 PM) have 30% more traffic
        if (8 <= hour < 10) or (17 <= hour < 19):
            return 1.3  # 30% longer travel time
        # Mid-day (12-2 PM) has 15% more traffic
        elif 12 <= hour < 14:
            return 1.15
        # Night (10 PM - 6 AM) has less traffic
        elif 22 <= hour or hour < 6:
            return 0.85
        # Other times are normal
        else:
            return 1.0