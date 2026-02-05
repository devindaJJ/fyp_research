from typing import List, Optional, Dict
from ..models.route import Route, RouteAlternative
from ..api.google_maps_client import GoogleMapsClient
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class RouteOptimizer:
    """Optimizes routes based on multiple criteria."""
    
    def __init__(self, google_maps_client: GoogleMapsClient):
        self.gmaps = google_maps_client
    
    def find_optimal_route(
        self,
        origin: str,
        destination: str,
        preferences: Optional[Dict] = None
    ) -> Optional[Route]:
        """
        Find optimal route based on user preferences.
        
        Preferences can include:
        - avoid_tolls: bool
        - avoid_highways: bool
        - preference: 'fastest', 'shortest', 'scenic'
        - max_additional_time: float (max additional minutes willing to spend)
        """
        if preferences is None:
            preferences = {}
        
        # Get multiple route alternatives
        routes = self.gmaps.get_route_alternatives(
            origin=origin,
            destination=destination,
            alternatives_count=5
        )
        
        if not routes:
            return None
        
        # Score each route based on preferences
        scored_routes = []
        for route_data in routes:
            score = self._calculate_route_score(route_data, preferences)
            scored_routes.append((score, route_data))
        
        # Select best route
        scored_routes.sort(key=lambda x: x[0], reverse=True)
        best_score, best_route_data = scored_routes[0]
        
        # Parse and return best route
        return self._parse_route(best_route_data)
    
    def _calculate_route_score(self, route_data: Dict, preferences: Dict) -> float:
        """Calculate score for a route based on preferences."""
        score = 0.0
        
        leg = route_data['legs'][0]
        duration = leg.get('duration_in_traffic', {}).get('value', leg['duration']['value']) / 60
        distance = leg['distance']['value'] / 1000  # Convert to km
        
        # Base score from duration (normalized)
        # Assuming typical Sri Lanka speeds: 30-40 km/h average
        estimated_optimal_time = (distance / 35) * 60  # minutes
        time_score = max(0, 1 - (duration - estimated_optimal_time) / estimated_optimal_time)
        score += time_score * 0.6  # 60% weight
        
        # Check for tolls
        if preferences.get('avoid_tolls', False):
            has_tolls = self._check_for_tolls(route_data)
            if not has_tolls:
                score += 0.2  # Bonus for no tolls
        
        # Check for highways
        if preferences.get('avoid_highways', False):
            has_highways = self._check_for_highways(route_data)
            if not has_highways:
                score += 0.1
        
        # Additional preferences
        if preferences.get('preference') == 'scenic':
            # Prefer routes with curves (indicating hill roads in Sri Lanka)
            curves = self._count_curves(route_data)
            score += min(curves / 20, 0.1)  # Max 0.1 bonus for scenic
        
        return score
    
    def _check_for_tolls(self, route_data: Dict) -> bool:
        """Check if route has tolls."""
        # This is a simplified check
        toll_keywords = ['toll', 'expressway', 'E', '收费', '有料']
        
        for step in route_data['legs'][0]['steps']:
            instruction = step.get('html_instructions', '').lower()
            if any(keyword in instruction for keyword in toll_keywords):
                return True
        
        return False
    
    def _check_for_highways(self, route_data: Dict) -> bool:
        """Check if route uses highways."""
        highway_keywords = ['highway', 'expressway', 'motorway', 'E1', 'E2', 'E3']
        
        for step in route_data['legs'][0]['steps']:
            instruction = step.get('html_instructions', '').lower()
            if any(keyword in instruction for keyword in highway_keywords):
                return True
        
        return False
    
    def _count_curves(self, route_data: Dict) -> int:
        """Count curves in route (approximate)."""
        # Simplified: count direction changes in steps
        direction_keywords = ['left', 'right', 'turn', 'roundabout']
        curve_count = 0
        
        for step in route_data['legs'][0]['steps']:
            instruction = step.get('html_instructions', '').lower()
            if any(keyword in instruction for keyword in direction_keywords):
                curve_count += 1
        
        return curve_count
    
    def _parse_route(self, route_data: Dict) -> Route:
        """Parse Google Maps route data into Route object."""
        leg = route_data['legs'][0]
        
        from ..models.route import Route, RouteStep
        
        steps = []
        for step in leg['steps']:
            steps.append(RouteStep(
                instruction=step['html_instructions'],
                distance_text=step['distance']['text'],
                distance_meters=step['distance']['value'],
                duration_text=step['duration']['text'],
                duration_seconds=step['duration']['value'],
                polyline=step.get('polyline', {}).get('points', '')
            ))
        
        normal_duration = leg['duration']['value'] / 60
        traffic_duration = leg.get('duration_in_traffic', {}).get('value', leg['duration']['value']) / 60
        
        from ..models.traffic import TrafficLevel
        delay = traffic_duration - normal_duration
        traffic_level = self._determine_traffic_level(delay)
        
        return Route(
            origin=leg['start_address'],
            destination=leg['end_address'],
            normal_duration=normal_duration,
            traffic_duration=traffic_duration,
            delay_minutes=delay,
            distance_meters=leg['distance']['value'],
            distance_text=leg['distance']['text'],
            traffic_level=traffic_level,
            summary=route_data.get('summary', 'Route'),
            steps=steps,
            polyline=route_data.get('overview_polyline', {}).get('points', ''),
            is_primary=True
        )
    
    def _determine_traffic_level(self, delay_minutes: float):
        """Determine traffic level based on delay."""
        from ..models.traffic import TrafficLevel
        
        if delay_minutes <= 5:
            return TrafficLevel.LIGHT
        elif delay_minutes <= 15:
            return TrafficLevel.MODERATE
        elif delay_minutes <= 30:
            return TrafficLevel.HEAVY
        else:
            return TrafficLevel.SEVERE