"""
Validation utilities for Urban Traffic System
"""
import re
from typing import Optional, Tuple
from ..models.location import Location


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
    
    Returns:
        True if coordinates are valid
    """
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def validate_sri_lanka_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate if coordinates are within Sri Lanka bounds.
    
    Args:
        latitude: Latitude value
        longitude: Longitude value
    
    Returns:
        True if coordinates are in Sri Lanka
    """
    sri_lanka_bounds = {
        'min_lat': 5.5, 'max_lat': 10.0,
        'min_lon': 79.5, 'max_lon': 82.0
    }
    
    return (
        sri_lanka_bounds['min_lat'] <= latitude <= sri_lanka_bounds['max_lat'] and
        sri_lanka_bounds['min_lon'] <= longitude <= sri_lanka_bounds['max_lon']
    )


def validate_address(address: str) -> bool:
    """
    Validate address string.
    
    Args:
        address: Address string
    
    Returns:
        True if address appears valid
    """
    if not address or len(address.strip()) < 3:
        return False
    
    # Check for minimum components (at least city)
    components = [c.strip() for c in address.split(',') if c.strip()]
    return len(components) >= 1


def validate_sri_lanka_address(address: str) -> bool:
    """
    Validate if address appears to be in Sri Lanka.
    
    Args:
        address: Address string
    
    Returns:
        True if address appears to be in Sri Lanka
    """
    address_lower = address.lower()
    
    # Check for Sri Lanka or LK
    if 'sri lanka' in address_lower or ', lk' in address_lower:
        return True
    
    # Check for Sri Lankan cities
    sri_lankan_cities = [
        'colombo', 'kandy', 'galle', 'jaffna', 'negombo',
        'matara', 'anuradhapura', 'trincomalee', 'batticaloa',
        'ratnapura', 'nuwara eliya', 'kurunegala', 'badulla',
        'puttalam', 'hambantota', 'kalutara', 'gampaha',
        'kegalle', 'moneragala', 'polonnaruwa', 'vavuniya'
    ]
    
    for city in sri_lankan_cities:
        if city in address_lower:
            return True
    
    return False


def parse_coordinates_string(coords_str: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from string.
    
    Args:
        coords_str: Coordinates string (e.g., "6.9271, 79.8612")
    
    Returns:
        Tuple of (latitude, longitude) or None if invalid
    """
    try:
        # Remove parentheses and split
        coords_str = coords_str.strip('()[]{}')
        parts = [p.strip() for p in coords_str.split(',')]
        
        if len(parts) != 2:
            return None
        
        lat = float(parts[0])
        lon = float(parts[1])
        
        if validate_coordinates(lat, lon):
            return (lat, lon)
        
        return None
        
    except (ValueError, AttributeError):
        return None


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address.
    
    Args:
        ip: IP address string
    
    Returns:
        True if IP address is valid
    """
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    
    if re.match(ipv4_pattern, ip):
        parts = ip.split('.')
        if all(0 <= int(part) <= 255 for part in parts):
            return True
    
    if re.match(ipv6_pattern, ip):
        return True
    
    return False


def validate_location(location: Location) -> Tuple[bool, str]:
    """
    Validate Location object.
    
    Args:
        location: Location object
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not validate_coordinates(location.latitude, location.longitude):
        return False, "Invalid coordinates"
    
    if not validate_sri_lanka_coordinates(location.latitude, location.longitude):
        return False, "Coordinates outside Sri Lanka"
    
    if not location.address or len(location.address.strip()) < 5:
        return False, "Address too short"
    
    if location.accuracy < 0 or location.accuracy > 1:
        return False, "Invalid accuracy value"
    
    return True, "Valid location"