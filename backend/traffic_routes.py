"""
Traffic analysis API routes
Integrates the main traffic system with the Flask backend
"""
import os
import sys
from datetime import datetime
from flask import Blueprint, jsonify, request

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.google_maps_client import GoogleMapsClient
from src.core.location_service import LocationService
from src.core.traffic_analyzer import TrafficAnalyzer
from src.core.route_optimizer import RouteOptimizer

# Create Blueprint
traffic_bp = Blueprint('traffic', __name__)

# Initialize components (lazy)
_gmaps_client = None
_location_service = None
_traffic_analyzer = None
_route_optimizer = None


def get_traffic_components():
    """Initialize traffic system components lazily."""
    global _gmaps_client, _location_service, _traffic_analyzer, _route_optimizer
    
    if _gmaps_client is None:
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_MAPS_API_KEY not found in environment variables")
        
        _gmaps_client = GoogleMapsClient(api_key)
        _location_service = LocationService(_gmaps_client.client)
        _traffic_analyzer = TrafficAnalyzer(_gmaps_client)
        _route_optimizer = RouteOptimizer(_gmaps_client)
    
    return {
        'gmaps': _gmaps_client,
        'location': _location_service,
        'analyzer': _traffic_analyzer,
        'optimizer': _route_optimizer
    }


@traffic_bp.route('/api/traffic/current-location', methods=['GET'])
def get_current_location():
    """Get automatically detected current location."""
    try:
        components = get_traffic_components()
        location = components['location'].detect_current_location()
        
        if not location:
            return jsonify({
                "success": False,
                "error": "Could not detect current location"
            }), 404
        
        return jsonify({
            "success": True,
            "location": {
                "address": location.address,
                "city": location.city,
                "country": location.country,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "accuracy": location.accuracy,
                "source": location.source
            }
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500




@traffic_bp.route('/api/traffic/analyze-route', methods=['POST'])
def analyze_route():
    """
    Analyze route with automatic location detection.
    Request body: { "destination": "Location, Sri Lanka" }
    Optional: { "origin": "...", "destination": "..." }
    """
    try:
        data = request.get_json()
        
        if not data or 'destination' not in data:
            return jsonify({
                "success": False,
                "error": "Destination is required"
            }), 400
        
        components = get_traffic_components()
        destination = data['destination']
        
        # Get origin (either from request or auto-detect)
        if 'origin' in data and data['origin']:
            origin = data['origin']
        else:
            current_location = components['location'].detect_current_location()
            if not current_location:
                return jsonify({
                    "success": False,
                    "error": "Could not detect current location. Please provide origin."
                }), 400
            origin = current_location.address
        
        # Analyze route
        analysis = components['analyzer'].analyze_route(origin, destination)
        
        if not analysis:
            return jsonify({
                "success": False,
                "error": "Could not analyze route"
            }), 404
        
        # Convert analysis to JSON-serializable format
        response_data = {
            "success": True,
            "analysis": {
                "origin": analysis.primary_route.origin,
                "destination": analysis.primary_route.destination,
                "analysis_time": analysis.analysis_time.isoformat(),
                "primary_route": {
                    "summary": analysis.primary_route.summary,
                    "distance_text": analysis.primary_route.distance_text,
                    "distance_km": analysis.primary_route.distance_km,
                    "normal_duration": analysis.primary_route.normal_duration,
                    "traffic_duration": analysis.primary_route.traffic_duration,
                    "delay_minutes": analysis.primary_route.delay_minutes,
                    "delay_percentage": analysis.primary_route.delay_percentage,
                    "traffic_level": analysis.primary_route.traffic_level.value,
                    "polyline": analysis.primary_route.polyline,
                    "segments": [
                        {
                            "polyline": s.get('polyline', ''),
                            "points": s.get('points', []),
                            "delay_minutes": s.get('delay_minutes', 0),
                            "traffic_level": (s.get('traffic_level').value if hasattr(s.get('traffic_level'), 'value') else s.get('traffic_level')),
                            "distance": s.get('distance')
                        }
                        for s in analysis.primary_route.steps
                    ]
                },
                "congestion": {
                    "level": analysis.congestion_level.value,
                    "description": analysis.congestion_level.get_description(),
                    "delay_minutes": analysis.delay_minutes
                },
                "alternatives": [
                    {
                        "summary": alt.summary,
                        "distance_text": alt.distance_text,
                        "distance_km": alt.distance_km,
                        "traffic_duration": alt.traffic_duration,
                        "delay_minutes": alt.delay_minutes,
                        "traffic_level": alt.traffic_level.value,
                        "polyline": alt.polyline
                    }
                    for alt in analysis.alternatives
                ],
                "recommendation": {
                    "should_reroute": analysis.should_reroute,
                    "alternative": {
                        "summary": analysis.recommended_alternative.summary,
                        "traffic_duration": analysis.recommended_alternative.traffic_duration,
                        "time_savings": analysis.delay_minutes - analysis.recommended_alternative.delay_minutes,
                        "traffic_level": analysis.recommended_alternative.traffic_level.value
                    } if analysis.recommended_alternative else None
                }
            }
        }
        
        return jsonify(response_data)
    
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@traffic_bp.route('/api/traffic/compare-destinations', methods=['POST'])
def compare_destinations():
    """
    Compare traffic to multiple destinations from current location.
    Request body: { "destinations": ["Location 1", "Location 2", ...] }
    Optional: { "origin": "...", "destinations": [...] }
    """
    try:
        data = request.get_json()
        
        if not data or 'destinations' not in data:
            return jsonify({
                "success": False,
                "error": "Destinations list is required"
            }), 400
        
        destinations = data['destinations']
        
        if not isinstance(destinations, list) or len(destinations) < 2:
            return jsonify({
                "success": False,
                "error": "At least 2 destinations required"
            }), 400
        
        components = get_traffic_components()
        
        # Get origin
        if 'origin' in data and data['origin']:
            origin = data['origin']
        else:
            current_location = components['location'].detect_current_location()
            if not current_location:
                return jsonify({
                    "success": False,
                    "error": "Could not detect current location. Please provide origin."
                }), 400
            origin = current_location.address

        # Analyze each destination
        results = []
        for destination in destinations:
            try:
                analysis = components['analyzer'].analyze_route(origin, destination)
                
                if analysis:
                    results.append({
                        "destination": destination,
                        "time": analysis.primary_route.traffic_duration,
                        "delay": analysis.delay_minutes,
                        "traffic_level": analysis.congestion_level.value,
                        "distance": analysis.primary_route.distance_text,
                        "should_reroute": analysis.should_reroute
                    })
            except Exception as e:
                results.append({
                    "destination": destination,
                    "error": str(e)
                })
        
        # Sort by travel time
        results_sorted = sorted(
            [r for r in results if 'time' in r],
            key=lambda x: x['time']
        )
        
        return jsonify({
            "success": True,
            "origin": origin,
            "results": results_sorted,
            "fastest": results_sorted[0] if results_sorted else None
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@traffic_bp.route('/api/traffic/location-suggestions', methods=['GET'])
def location_suggestions():
    """Provide simple location suggestions from local config (no external API required)."""
    try:
        q = (request.args.get('q') or '').strip().lower()
        import json
        cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'sri_lanka_locations.json')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            loc_data = json.load(f)

        candidates = []
        # Major cities
        for city, meta in loc_data.get('major_cities', {}).items():
            candidates.append({
                'label': city,
                'center': meta.get('center', city),
                'latitude': meta.get('latitude'),
                'longitude': meta.get('longitude')
            })
        # Popular route centers
        for k, v in loc_data.get('popular_routes', {}).items():
            candidates.append({
                'label': v.get('start'),
                'center': v.get('start')
            })
            candidates.append({
                'label': v.get('end'),
                'center': v.get('end')
            })
        # Hotspots
        for area, points in loc_data.get('traffic_hotspots', {}).items():
            for p in points:
                candidates.append({
                    'label': p.get('name'),
                    'center': p.get('name'),
                    'latitude': p.get('lat'),
                    'longitude': p.get('lon')
                })

        # Deduplicate by label while preserving order
        seen = set()
        unique = []
        for c in candidates:
            lab = c['label']
            if lab not in seen:
                seen.add(lab)
                unique.append(c)

        if q:
            filtered = [c for c in unique if q in c['label'].lower() or q in (c.get('center') or '').lower()]
        else:
            filtered = unique[:20]

        return jsonify({
            'success': True,
            'suggestions': filtered[:20]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@traffic_bp.route('/api/traffic/reroute-advice', methods=['POST'])
def get_reroute_advice():
    """
    Get detailed rerouting advice for a route.
    Request body: { "origin": "...", "destination": "..." }
    """
    try:
        data = request.get_json()
        
        if not data or 'destination' not in data:
            return jsonify({
                "success": False,
                "error": "Destination is required"
            }), 400
        
        components = get_traffic_components()
        destination = data['destination']
        
        # Get origin
        if 'origin' in data and data['origin']:
            origin = data['origin']
        else:
            current_location = components['location'].detect_current_location()
            if not current_location:
                return jsonify({
                    "success": False,
                    "error": "Could not detect current location. Please provide origin."
                }), 400
            origin = current_location.address
        
        # Analyze route
        analysis = components['analyzer'].analyze_route(origin, destination)
        
        if not analysis:
            return jsonify({
                "success": False,
                "error": "Could not analyze route"
            }), 404
        
        # Get detailed advice
        advice = components['analyzer'].get_detailed_reroute_advice(analysis)
        
        return jsonify({
            "success": True,
            "advice": advice
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
