"""
Geolocation API for automatic location detection
"""
import requests
import socket
import json
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class GeoLocation:
    """Geolocation data class."""
    latitude: float
    longitude: float
    city: str
    region: str
    country: str
    country_code: str
    timezone: str
    isp: str = ""
    accuracy: float = 1.0
    source: str = "unknown"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "country_code": self.country_code,
            "timezone": self.timezone,
            "isp": self.isp,
            "accuracy": self.accuracy,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


class GeolocationAPI:
    """Geolocation service using multiple providers."""
    
    def __init__(self, ipinfo_token: str = None, cache_duration: int = 3600):
        self.ipinfo_token = ipinfo_token
        self.cache_duration = cache_duration  # seconds
        self.cache = {}
        self.services = [
            self._get_location_ipinfo,
            self._get_location_ipapi,
            self._get_location_geolocation_db,
            self._get_location_ipstack
        ]
    
    def get_location(self, ip_address: str = None) -> Optional[GeoLocation]:
        """Get location using multiple services with fallback."""
        if ip_address is None:
            ip_address = self._get_public_ip()
            if not ip_address:
                return None
        
        # Check cache
        cache_key = f"location_{ip_address}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                logger.debug(f"Using cached location for {ip_address}")
                return cached_data
        
        # Try all services
        location = None
        for service in self.services:
            try:
                location = service(ip_address)
                if location:
                    logger.info(f"Location found via {service.__name__} for {ip_address}")
                    break
            except Exception as e:
                logger.debug(f"Service {service.__name__} failed: {e}")
                continue
        
        if location:
            # Cache the result
            self.cache[cache_key] = (location, datetime.now())
        
        return location
    
    def _get_location_ipinfo(self, ip_address: str) -> Optional[GeoLocation]:
        """Get location using IPInfo.io."""
        try:
            if self.ipinfo_token:
                url = f"https://ipinfo.io/{ip_address}?token={self.ipinfo_token}"
            else:
                url = f"https://ipinfo.io/{ip_address}/json"
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                if 'loc' in data:
                    lat, lon = data['loc'].split(',')
                    return GeoLocation(
                        latitude=float(lat),
                        longitude=float(lon),
                        city=data.get('city', 'Unknown'),
                        region=data.get('region', 'Unknown'),
                        country=data.get('country', 'Unknown'),
                        country_code=data.get('country', ''),
                        timezone=data.get('timezone', 'UTC'),
                        isp=data.get('org', ''),
                        accuracy=0.9,
                        source="ipinfo.io"
                    )
        except Exception as e:
            logger.debug(f"IPInfo service error: {e}")
        
        return None
    
    def _get_location_ipapi(self, ip_address: str) -> Optional[GeoLocation]:
        """Get location using ip-api.com (free)."""
        try:
            url = f"http://ip-api.com/json/{ip_address}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return GeoLocation(
                        latitude=data['lat'],
                        longitude=data['lon'],
                        city=data.get('city', 'Unknown'),
                        region=data.get('regionName', 'Unknown'),
                        country=data.get('country', 'Unknown'),
                        country_code=data.get('countryCode', ''),
                        timezone=data.get('timezone', 'UTC'),
                        isp=data.get('isp', ''),
                        accuracy=0.8,
                        source="ip-api.com"
                    )
        except Exception as e:
            logger.debug(f"IP-API service error: {e}")
        
        return None
    
    def _get_location_geolocation_db(self, ip_address: str) -> Optional[GeoLocation]:
        """Get location using geolocation-db.com."""
        try:
            url = f"https://geolocation-db.com/json/{ip_address}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('latitude') and data.get('longitude'):
                    return GeoLocation(
                        latitude=float(data['latitude']),
                        longitude=float(data['longitude']),
                        city=data.get('city', 'Unknown'),
                        region=data.get('state', 'Unknown'),
                        country=data.get('country_name', 'Unknown'),
                        country_code=data.get('country_code', ''),
                        timezone='UTC',
                        accuracy=0.7,
                        source="geolocation-db.com"
                    )
        except Exception as e:
            logger.debug(f"Geolocation DB service error: {e}")
        
        return None
    
    def _get_location_ipstack(self, ip_address: str) -> Optional[GeoLocation]:
        """Get location using ipstack.com (requires API key)."""
        # This is a placeholder - you'd need an API key for ipstack
        # Uncomment and add your API key if you have one
        """
        try:
            api_key = os.getenv('IPSTACK_API_KEY')
            if api_key:
                url = f"http://api.ipstack.com/{ip_address}?access_key={api_key}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('latitude') and data.get('longitude'):
                        return GeoLocation(
                            latitude=data['latitude'],
                            longitude=data['longitude'],
                            city=data.get('city', 'Unknown'),
                            region=data.get('region_name', 'Unknown'),
                            country=data.get('country_name', 'Unknown'),
                            country_code=data.get('country_code', ''),
                            timezone=data.get('time_zone', {}).get('id', 'UTC'),
                            accuracy=0.95,
                            source="ipstack.com"
                        )
        except Exception as e:
            logger.debug(f"IPStack service error: {e}")
        """
        return None
    
    def _get_public_ip(self) -> Optional[str]:
        """Get public IP address."""
        services = [
            'https://api.ipify.org',
            'https://icanhazip.com',
            'https://ident.me',
            'https://checkip.amazonaws.com'
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=3)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if self._is_valid_ip(ip):
                        return ip
            except:
                continue
        
        # Fallback: get from socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if string is a valid IP address."""
        try:
            socket.inet_pton(socket.AF_INET, ip)
            return True
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, ip)
                return True
            except socket.error:
                return False
    
    def is_in_sri_lanka(self, location: GeoLocation) -> bool:
        """Check if location is in Sri Lanka."""
        sri_lanka_bounds = {
            'min_lat': 5.5, 'max_lat': 10.0,
            'min_lon': 79.5, 'max_lon': 82.0
        }
        
        return (
            sri_lanka_bounds['min_lat'] <= location.latitude <= sri_lanka_bounds['max_lat'] and
            sri_lanka_bounds['min_lon'] <= location.longitude <= sri_lanka_bounds['max_lon']
        )