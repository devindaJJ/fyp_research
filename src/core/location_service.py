import requests
import socket
import json
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from ipinfo import getHandler
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass
class Location:
    """Data class for location information."""
    latitude: float
    longitude: float
    address: str
    city: str
    country: str
    accuracy: float = 1.0
    source: str = "unknown"

    def to_coordinates(self) -> str:
        return f"{self.latitude},{self.longitude}"

    def is_in_sri_lanka(self) -> bool:
        sri_lanka_bounds = {
            'min_lat': 5.5, 'max_lat': 10.0,
            'min_lon': 79.5, 'max_lon': 82.0
        }
        return (
            sri_lanka_bounds['min_lat'] <= self.latitude <= sri_lanka_bounds['max_lat'] and
            sri_lanka_bounds['min_lon'] <= self.longitude <= sri_lanka_bounds['max_lon']
        )


class LocationService:
    """Service for automatic location detection using multiple methods."""
    
    def __init__(self, google_maps_client: Optional[Any] = None):
        self.gmaps = google_maps_client
        self.geolocator = Nominatim(user_agent="sri_lanka_traffic_system")
        self.ipinfo_handler = None
        
        # Try to initialize IPInfo with token if available
        try:
            import os
            ipinfo_token = os.getenv('IPINFO_TOKEN')
            if ipinfo_token:
                self.ipinfo_handler = getHandler(ipinfo_token)
        except:
            logger.warning("IPInfo token not available, using free tier")
            self.ipinfo_handler = getHandler()
    
    def detect_current_location(self) -> Optional[Location]:
        """
        Automatically detect current location using multiple fallback methods.
        Returns the most accurate location found.
        """
        location_methods = [
            self._get_location_via_ipinfo,
            self._get_location_via_public_ip,
            self._get_location_via_network,
        ]
        
        locations = []
        for method in location_methods:
            try:
                loc = method()
                if loc and self._is_in_sri_lanka(loc):
                    locations.append(loc)
                    logger.info(f"Location detected via {method.__name__}: {loc.address}")
            except Exception as e:
                logger.warning(f"Location method failed: {e}")
                continue
        
        if not locations:
            logger.error("Could not detect current location")
            return None
        
        # Return the most accurate location
        return max(locations, key=lambda x: x.accuracy)
    
    def _get_location_via_ipinfo(self) -> Optional[Location]:
        """Get location using IPInfo service."""
        try:
            if not self.ipinfo_handler:
                return None
                
            # Get IP address
            ip = self._get_public_ip()
            if not ip:
                return None
                
            # Get location details
            details = self.ipinfo_handler.getDetails(ip)
            
            if details.loc:
                lat, lon = details.loc.split(',')
                return Location(
                    latitude=float(lat),
                    longitude=float(lon),
                    address=f"{details.city}, {details.region}, {details.country}",
                    city=details.city or "Unknown",
                    country=details.country or "Unknown",
                    accuracy=0.9,
                    source="ipinfo"
                )
        except Exception as e:
            logger.error(f"IPInfo location failed: {e}")
        
        return None
    
    def _get_location_via_public_ip(self) -> Optional[Location]:
        """Get location using public IP geolocation services."""
        try:
            # Get public IP
            ip = self._get_public_ip()
            if not ip:
                return None
            
            # Use ip-api.com (free service)
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    return Location(
                        latitude=data['lat'],
                        longitude=data['lon'],
                        address=f"{data['city']}, {data['regionName']}, {data['country']}",
                        city=data['city'],
                        country=data['country'],
                        accuracy=0.8,
                        source="ip-api"
                    )
        except Exception as e:
            logger.error(f"Public IP location failed: {e}")
        
        return None
    
    def _get_location_via_network(self) -> Optional[Location]:
        """Get approximate location based on network information."""
        try:
            # Get hostname and local IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # For Sri Lanka, we can make educated guesses based on common IP ranges
            # This is a fallback method with lower accuracy
            sri_lanka_cities = {
                "Colombo": (6.9271, 79.8612),
                "Kandy": (7.2906, 80.6337),
                "Galle": (6.0535, 80.2210),
                "Jaffna": (9.6615, 80.0255),
                "Negombo": (7.2096, 79.8357),
            }
            
            # Use Colombo as default for Sri Lanka
            lat, lon = sri_lanka_cities["Colombo"]
            return Location(
                latitude=lat,
                longitude=lon,
                address="Colombo, Western Province, Sri Lanka",
                city="Colombo",
                country="Sri Lanka",
                accuracy=0.3,  # Low accuracy
                source="network_fallback"
            )
        except Exception as e:
            logger.error(f"Network location failed: {e}")
        
        return None
    
    def _get_public_ip(self) -> Optional[str]:
        """Get public IP address."""
        try:
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://ident.me'
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=3)
                    if response.status_code == 200:
                        return response.text.strip()
                except:
                    continue
        except:
            pass
        
        return None
    
    def _is_in_sri_lanka(self, location: Location) -> bool:
        """Check if location is within Sri Lanka bounds."""
        # Sri Lanka approximate bounds
        sri_lanka_bounds = {
            'min_lat': 5.5, 'max_lat': 10.0,
            'min_lon': 79.5, 'max_lon': 82.0
        }
        
        return (
            sri_lanka_bounds['min_lat'] <= location.latitude <= sri_lanka_bounds['max_lat'] and
            sri_lanka_bounds['min_lon'] <= location.longitude <= sri_lanka_bounds['max_lon']
        )
    
    def geocode_address(self, address: str) -> Optional[Location]:
        """Convert address string to Location object."""
        try:
            if not address.lower().endswith("sri lanka"):
                address = f"{address}, Sri Lanka"
            
            location = self.geolocator.geocode(address, timeout=10)
            if location:
                return Location(
                    latitude=location.latitude,
                    longitude=location.longitude,
                    address=location.address,
                    city=self._extract_city(location.address),
                    country="Sri Lanka",
                    accuracy=0.95,
                    source="geocoding"
                )
        except Exception as e:
            logger.error(f"Geocoding failed for {address}: {e}")
        
        return None
    
    def _extract_city(self, address: str) -> str:
        """Extract city name from address string."""
        # Simple extraction - can be enhanced
        sri_lanka_cities = [
            "Colombo", "Kandy", "Galle", "Jaffna", "Negombo",
            "Matara", "Anuradhapura", "Trincomalee", "Batticaloa",
            "Ratnapura", "Nuwara Eliya", "Kurunegala", "Badulla"
        ]
        
        for city in sri_lanka_cities:
            if city.lower() in address.lower():
                return city
        
        return "Unknown"