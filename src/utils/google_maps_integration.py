"""
Google Maps API integration for dynamic speed limits and location context.
"""
import googlemaps
from typing import Dict, Optional


class GoogleMapsRoadContext:
    """Fetch road information using Google Maps API"""
    
    def __init__(self, api_key: str):
        """
        Initialize Google Maps client.
        
        Args:
            api_key: Your Google Maps API key
        """
        if not api_key:
            raise ValueError("Google Maps API key is required")
        
        self.gmaps = googlemaps.Client(key=api_key)
        self.cache = {}  # Cache to reduce API calls
        print("Google Maps integration initialized")
    
    def get_speed_limit_by_address(self, address: str) -> Optional[Dict]:
        """
        Get speed limit for a road address.
        
        Args:
            address: Road address (e.g., "Galle Road, Colombo, Sri Lanka")
            
        Returns:
            Dictionary with speed limit and location info
        """
        # Check cache first
        if address in self.cache:
            print(f"Using cached data for: {address}")
            return self.cache[address]
        
        try:
            print(f"Fetching road data from Google Maps for: {address}")
            
            # Step 1: Geocode the address to get coordinates
            geocode_result = self.gmaps.geocode(address)
            
            if not geocode_result:
                print(f"Could not geocode address: {address}")
                return {'speed_limit': 60, 'units': 'KPH', 'source': 'default'}
            
            location = geocode_result[0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            formatted_address = geocode_result[0]['formatted_address']
            
            print(f"  Location: {formatted_address}")
            print(f"  Coordinates: ({lat:.6f}, {lng:.6f})")
            
            # Step 2: Snap to nearest road
            snapped = self.gmaps.snap_to_roads(
                path=[(lat, lng)],
                interpolate=False
            )
            
            if not snapped.get('snappedPoints'):
                print("  Could not snap to road, using default speed limit")
                return {'speed_limit': 60, 'units': 'KPH', 'source': 'default'}
            
            place_id = snapped['snappedPoints'][0]['placeId']
            
            # Step 3: Get speed limit using place ID
            speed_result = self.gmaps.speed_limits(place_ids=[place_id])
            
            if speed_result.get('speedLimits'):
                speed_info = speed_result['speedLimits'][0]
                
                result = {
                    'speed_limit': speed_info.get('speedLimit', 60),
                    'units': speed_info.get('units', 'KPH'),
                    'address': formatted_address,
                    'latitude': lat,
                    'longitude': lng,
                    'source': 'google_maps'
                }
                
                print(f"  ✓ Speed Limit: {result['speed_limit']} {result['units']}")
                
                # Cache the result
                self.cache[address] = result
                return result
            else:
                print("  No speed limit data available, using default")
                return {
                    'speed_limit': 60,
                    'units': 'KPH',
                    'source': 'default',
                    'address': formatted_address
                }
                
        except Exception as e:
            print(f"Error fetching speed limit: {e}")
            return {'speed_limit': 60, 'units': 'KPH', 'source': 'default'}
    
    def check_special_zones(self, latitude: float, longitude: float, 
                           radius: int = 500) -> Dict:
        """
        Check for special zones nearby (schools, hospitals, etc.)
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius: Search radius in meters (default: 500)
            
        Returns:
            Dictionary with zone information and adjusted speed limits
        """
        zones = {
            'school_zone': False,
            'hospital_zone': False,
            'adjusted_speed_limit': None,
            'zone_details': []
        }
        
        try:
            print(f"Checking for special zones near ({latitude:.6f}, {longitude:.6f})")
            
            # Check for schools within radius
            schools = self.gmaps.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                type='school'
            )
            
            if schools.get('results'):
                zones['school_zone'] = True
                zones['adjusted_speed_limit'] = 20  # Strict limit near schools
                school_name = schools['results'][0].get('name', 'Unknown School')
                zones['zone_details'].append({
                    'type': 'school',
                    'name': school_name,
                    'distance': f'within {radius}m'
                })
                print(f"  ⚠ School Zone detected: {school_name}")
                print(f"  ⚠ Adjusted speed limit: 20 KPH")
            
            # Check for hospitals within radius
            hospitals = self.gmaps.places_nearby(
                location=(latitude, longitude),
                radius=radius,
                type='hospital'
            )
            
            if hospitals.get('results'):
                zones['hospital_zone'] = True
                if zones['adjusted_speed_limit'] is None:
                    zones['adjusted_speed_limit'] = 30
                hospital_name = hospitals['results'][0].get('name', 'Unknown Hospital')
                zones['zone_details'].append({
                    'type': 'hospital',
                    'name': hospital_name,
                    'distance': f'within {radius}m'
                })
                print(f"  ⚠ Hospital Zone detected: {hospital_name}")
                if zones['adjusted_speed_limit'] == 30:
                    print(f"  ⚠ Adjusted speed limit: 30 KPH")
            
            if not zones['school_zone'] and not zones['hospital_zone']:
                print("  ✓ No special zones detected")
            
            return zones
            
        except Exception as e:
            print(f"Error checking special zones: {e}")
            return zones
    
    def get_complete_road_context(self, address: str) -> Dict:
        """
        Get comprehensive road context including speed limit, zones, and road info.
        
        Args:
            address: Road address
            
        Returns:
            Complete road context dictionary
        """
        print("\n" + "="*80)
        print("FETCHING ROAD CONTEXT FROM GOOGLE MAPS")
        print("="*80)
        
        # Get speed limit and location
        road_data = self.get_speed_limit_by_address(address)
        
        if not road_data:
            return {'error': 'Could not fetch road data'}
        
        context = {
            'address': road_data.get('address', address),
            'speed_limit': road_data.get('speed_limit', 60),
            'units': road_data.get('units', 'KPH'),
            'source': road_data.get('source', 'default')
        }
        
        # Check for special zones if coordinates available
        if 'latitude' in road_data and 'longitude' in road_data:
            zones = self.check_special_zones(
                road_data['latitude'],
                road_data['longitude']
            )
            context['zones'] = zones
            
            # Final speed limit considering zones
            if zones.get('adjusted_speed_limit'):
                context['final_speed_limit'] = zones['adjusted_speed_limit']
                context['reason'] = 'Special zone detected'
            else:
                context['final_speed_limit'] = context['speed_limit']
                context['reason'] = 'Normal road'
        else:
            context['final_speed_limit'] = context['speed_limit']
            context['reason'] = 'Default'
        
        print("="*80)
        print(f"FINAL SPEED LIMIT: {context['final_speed_limit']} KPH ({context['reason']})")
        print("="*80 + "\n")
        
        return context