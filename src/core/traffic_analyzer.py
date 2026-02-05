"""
Traffic Analyzer with robust type handling
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import time
from dataclasses import dataclass
from ..models.route import Route, RouteAlternative, TrafficLevel
from ..api.google_maps_client import GoogleMapsClient
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class TrafficAnalysis:
    """Comprehensive traffic analysis result."""
    primary_route: Route
    alternatives: List[RouteAlternative]
    recommended_alternative: Optional[RouteAlternative]
    congestion_level: TrafficLevel
    delay_minutes: float
    should_reroute: bool
    analysis_time: datetime


class TrafficAnalyzer:
    """Analyzes traffic conditions and suggests optimal routes."""
    
    def __init__(self, google_maps_client: GoogleMapsClient):
        self.gmaps = google_maps_client
        self.reroute_threshold = 15  # Suggest reroute for >15 min delay
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert any value to float."""
        if value is None:
            return default
        
        try:
            # If it's already a number
            if isinstance(value, (int, float)):
                return float(value)
            
            # If it's a string, try to convert
            if isinstance(value, str):
                # Remove any non-numeric characters except decimal point and minus
                cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
                if cleaned:
                    return float(cleaned)
            
            # Try direct conversion as last resort
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to float, using default {default}")
            return default
    
    def analyze_route(self, origin: str, destination: str) -> Optional[TrafficAnalysis]:
        """
        Analyze traffic for a route and suggest alternatives if congested.
        """
        try:
            logger.info(f"Analyzing route: {origin} → {destination}")
            
            # Get multiple route alternatives from Google Maps (default: 3 alternatives)
            routes_data = self.gmaps.get_route_alternatives(
                origin=origin,
                destination=destination,
                alternatives_count=3,
                departure_time="now",
                traffic_model="best_guess"
            )
            
            if not routes_data:
                logger.warning(f"No routes found between {origin} and {destination}")
                return None
            
            # Parse primary route
            primary_route = self._parse_route(routes_data[0], origin, destination, is_primary=True)
            if not primary_route:
                return None
            
            # Parse alternatives
            alternatives = []
            for route_data in routes_data[1:]:
                alternative = self._parse_route(route_data, origin, destination, is_primary=False)
                if alternative:
                    alternatives.append(alternative)
            
            # Calculate congestion metrics with safe conversion
            delay_minutes = self._safe_float(primary_route.traffic_duration - primary_route.normal_duration)
            congestion_level = self._determine_congestion_level(delay_minutes)
            
            # Convert alternatives to RouteAlternative objects
            route_alternatives = []
            for alt in alternatives:
                if isinstance(alt, Route):
                    route_alternatives.append(RouteAlternative(
                        origin=alt.origin,
                        destination=alt.destination,
                        normal_duration=alt.normal_duration,
                        traffic_duration=alt.traffic_duration,
                        delay_minutes=alt.delay_minutes,
                        distance_meters=alt.distance_meters,
                        distance_text=alt.distance_text,
                        traffic_level=alt.traffic_level,
                        summary=alt.summary,
                        steps=alt.steps,
                        polyline=alt.polyline,
                        is_primary=False,
                        confidence=alt.confidence,
                        advantage_score=0.0
                    ))
            alternatives = route_alternatives
            
            # Determine if rerouting is recommended
            should_reroute = self._should_reroute(congestion_level, delay_minutes)
            
            # Find best alternative if rerouting is recommended
            recommended_alternative = None
            if should_reroute and alternatives:
                recommended_alternative = self._select_best_alternative(
                    primary_route, alternatives, delay_minutes
                )
            
            return TrafficAnalysis(
                primary_route=primary_route,
                alternatives=alternatives,
                recommended_alternative=recommended_alternative,
                congestion_level=congestion_level,
                delay_minutes=delay_minutes,
                should_reroute=should_reroute,
                analysis_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing route {origin} → {destination}: {e}")
            return None
    
    def _parse_route(self, route_data: Dict, origin: str, destination: str, is_primary: bool = False) -> Optional[Route]:
        """Parse Google Maps route data into Route object with safe conversion."""
        try:
            leg = route_data['legs'][0]
            
            # Safely extract and convert duration values
            normal_seconds = self._safe_float(leg['duration']['value'])
            normal_minutes = normal_seconds / 60.0
            
            # Get traffic duration, fallback to normal if not available
            traffic_data = leg.get('duration_in_traffic', {})
            traffic_seconds = self._safe_float(traffic_data.get('value', leg['duration']['value']))
            traffic_minutes = traffic_seconds / 60.0
            
            # Calculate delay
            delay_minutes = self._safe_float(traffic_minutes - normal_minutes)
            
            # Extract distance with safe conversion
            distance_meters = self._safe_float(leg['distance']['value'])
            distance_text = leg['distance']['text']
            
            # Determine traffic level
            traffic_level = self._determine_congestion_level(delay_minutes)
            
            # Extract steps and compute per-step delay & traffic level
            steps = []
            # Precompute leg-level seconds for fallback allocation
            leg_normal_sec = normal_seconds
            leg_traffic_sec = traffic_seconds
            leg_delay_sec = max(0.0, leg_traffic_sec - leg_normal_sec)

            for step in leg.get('steps', []):
                step_normal_sec = self._safe_float(step.get('duration', {}).get('value'))

                # If step has explicit duration_in_traffic, use it; otherwise allocate leg delay proportionally
                if 'duration_in_traffic' in step and step.get('duration_in_traffic') and step.get('duration_in_traffic').get('value') is not None:
                    step_traffic_sec = self._safe_float(step.get('duration_in_traffic').get('value'))
                else:
                    if leg_normal_sec > 0:
                        # Allocate a share of leg delay based on step normal duration
                        step_traffic_sec = step_normal_sec + (leg_delay_sec * (step_normal_sec / leg_normal_sec))
                    else:
                        step_traffic_sec = step_normal_sec

                step_delay_min = (step_traffic_sec - step_normal_sec) / 60.0
                step_traffic_level = self._determine_congestion_level(step_delay_min)

                steps.append({
                    'instruction': step.get('html_instructions', ''),
                    'distance': step.get('distance', {}).get('text', ''),
                    'duration': step.get('duration', {}).get('text', ''),
                    'polyline': step.get('polyline', {}).get('points', ''),
                    'delay_minutes': step_delay_min,
                    'traffic_level': step_traffic_level,
                    'points': []  # will be filled later if missing
                })

            # If step polylines are missing, derive segment points by splitting the overview polyline coordinates
            overview_poly = route_data.get('overview_polyline', {}).get('points', '')
            if overview_poly:
                decoded_overview = self._decode_polyline(overview_poly)
                # Only split if steps present and any step lacks points
                if steps and any(not s['polyline'] for s in steps) and decoded_overview:
                    n = len(steps)
                    L = len(decoded_overview)
                    if L < 2:
                        # not enough points; give entire overview to first step
                        steps[0]['points'] = decoded_overview
                    else:
                        # Partition overview into n chunks with proportional division
                        for i, s in enumerate(steps):
                            start = int(round(i * L / n))
                            end = int(round((i + 1) * L / n))

                            # Ensure at least 2 points for a drawable segment when possible
                            if end <= start + 1 and i < n - 1:
                                end = min(start + 2, L)

                            if i == n - 1:
                                end = L

                            chunk = decoded_overview[start:end]
                            if not chunk:
                                # fallback to last two points
                                chunk = decoded_overview[-2:] if L >= 2 else decoded_overview
                            s['points'] = chunk
                else:
                    # For steps that have their own polylines, decode them into points
                    for s in steps:
                        if s['polyline']:
                            s['points'] = self._decode_polyline(s['polyline'])

            
            return Route(
                origin=leg.get('start_address', origin),
                destination=leg.get('end_address', destination),
                normal_duration=normal_minutes,
                traffic_duration=traffic_minutes,
                delay_minutes=delay_minutes,
                distance_meters=distance_meters,
                distance_text=distance_text,
                traffic_level=traffic_level,
                summary=route_data.get('summary', 'Route'),
                steps=steps,
                polyline=route_data.get('overview_polyline', {}).get('points', ''),
                is_primary=is_primary,
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error parsing route data: {e}")
            return None
    
    def _determine_congestion_level(self, delay_minutes: Any) -> TrafficLevel:
        """Determine traffic congestion level based on delay."""

        delay = self._safe_float(delay_minutes)
        
        if delay <= 5:
            return TrafficLevel.LIGHT
        elif delay <= 15:
            return TrafficLevel.MODERATE
        elif delay <= 30:
            return TrafficLevel.HEAVY
        else:
            return TrafficLevel.SEVERE

    def _decode_polyline(self, encoded: str):
        """Decode a Google encoded polyline into a list of (lat, lon) tuples."""
        if not encoded:
            return []

        points = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += dlat

            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            dlng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += dlng

            points.append((lat / 1e5, lng / 1e5))

        return points
    
    def _should_reroute(self, congestion_level: TrafficLevel, delay_minutes: float) -> bool:
        """Determine if rerouting is recommended."""
        
        if congestion_level.value in ['heavy', 'severe']:
            return True
        return delay_minutes > self.reroute_threshold
    
    def _select_best_alternative(
        self, 
        primary_route: Route, 
        alternatives: List[RouteAlternative],
        current_delay: float
    ) -> Optional[RouteAlternative]:
        """Select the best alternative route."""
        if not alternatives:
            return None
        
        scored_alternatives = []
        current_delay_float = self._safe_float(current_delay)
        
        for alt in alternatives:
            score = self._calculate_alternative_score(primary_route, alt, current_delay_float)
            scored_alternatives.append((score, alt))
        
        if not scored_alternatives:
            return None
        
        scored_alternatives.sort(key=lambda x: x[0], reverse=True)
        best_score, best_alternative = scored_alternatives[0]
        
        if best_score > 0.6:
            return best_alternative
        
        return None
    
    def _calculate_alternative_score(
        self, 
        primary: Route, 
        alternative: RouteAlternative, 
        current_delay: float
    ) -> float:
        """Calculate score for alternative route (0-1 scale)."""
        # Convert all values to floats safely
        current_delay_float = self._safe_float(current_delay)
        alt_delay_float = self._safe_float(alternative.delay_minutes)
        primary_distance = self._safe_float(primary.distance_meters)
        alt_distance = self._safe_float(alternative.distance_meters)
        
        score = 0.0
        
        # 1. Time savings (40% weight)
        if current_delay_float > 0:
            time_savings = current_delay_float - alt_delay_float
            if time_savings > 0:
                time_score = min(time_savings / current_delay_float, 1.0) * 0.4
                score += time_score
        
        # 2. Distance penalty (30% weight)
        if primary_distance > 0:
            distance_ratio = alt_distance / primary_distance
            if distance_ratio <= 1.2:  # ≤20% longer
                distance_score = (1.2 - distance_ratio) / 1.2 * 0.3
                score += distance_score
        
        # 3. Traffic level (20% weight)
        traffic_scores = {
            TrafficLevel.LIGHT: 0.2,
            TrafficLevel.MODERATE: 0.15,
            TrafficLevel.HEAVY: 0.05,
            TrafficLevel.SEVERE: 0.0,
            TrafficLevel.UNKNOWN: 0.0
        }
        score += traffic_scores.get(alternative.traffic_level, 0.0)
        complexity_penalty = min(len(alternative.steps) / 20, 0.1)
        score -= complexity_penalty
        
        return max(0.0, min(1.0, score))
    
    def analyze_with_auto_location(self, destination: str) -> Optional[TrafficAnalysis]:
        """Automatically detect current location and analyze route."""
        try:
            from .location_service import LocationService
            location_service = LocationService(self.gmaps.client)
            current_location = location_service.detect_current_location()
            
            if not current_location:
                logger.error("Could not detect current location")
                return None
            
            origin_address = current_location.address
            logger.info(f"Auto-detected location: {origin_address}")
            
            return self.analyze_route(origin_address, destination)
            
        except Exception as e:
            logger.error(f"Error in auto-location analysis: {e}")
            return None
    
    def get_detailed_reroute_advice(self, analysis: TrafficAnalysis) -> Dict[str, Any]:
        """Generate detailed rerouting advice."""
        advice = {
            'current_situation': {
                'congestion_level': analysis.congestion_level.value,
                'delay_minutes': round(analysis.delay_minutes, 1),
                'primary_route_time': round(analysis.primary_route.traffic_duration, 1),
                'normal_time': round(analysis.primary_route.normal_duration, 1)
            },
            'recommendation': 'Continue on current route',
            'alternatives_available': len(analysis.alternatives),
            'best_alternative': None,
            'estimated_savings': None,
            'reasoning': []
        }
        
        if analysis.should_reroute and analysis.recommended_alternative:
            alt = analysis.recommended_alternative
            time_savings = analysis.delay_minutes - alt.delay_minutes
            
            advice.update({
                'recommendation': f'Take alternative route via {alt.summary}',
                'best_alternative': {
                    'summary': alt.summary,
                    'estimated_time': round(alt.traffic_duration, 1),
                    'delay': round(alt.delay_minutes, 1),
                    'distance': alt.distance_text
                },
                'estimated_savings': round(time_savings, 1),
                'reasoning': [
                    f"Saves approximately {round(time_savings, 1)} minutes",
                    f"Traffic level: {alt.traffic_level.value} (vs {analysis.congestion_level.value})",
                    f"Route is {round((alt.distance_meters/analysis.primary_route.distance_meters - 1)*100, 1)}% longer"
                ]
            })
        
        elif analysis.should_reroute and not analysis.recommended_alternative:
            advice.update({
                'recommendation': 'Consider delaying your trip',
                'reasoning': [
                    "All alternative routes also have heavy traffic",
                    f"Current delay: {round(analysis.delay_minutes, 1)} minutes",
                    "Waiting 30-60 minutes might improve conditions"
                ]
            })
        
        return advice