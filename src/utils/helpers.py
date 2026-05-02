"""
Helper utilities for Urban Traffic System
"""
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f} hours"
    
    days = hours / 24
    return f"{days:.1f} days"


def format_distance(meters: float) -> str:
    """
    Format distance in meters to human-readable string.
    
    Args:
        meters: Distance in meters
    
    Returns:
        Formatted distance string
    """
    if meters < 1000:
        return f"{meters:.0f} meters"
    
    kilometers = meters / 1000
    return f"{kilometers:.1f} km"


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing between two points.
    
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Ending point coordinates
    
    Returns:
        Bearing in degrees (0-360)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)
    
    # Calculate bearing
    y = math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    
    bearing = math.degrees(math.atan2(y, x))
    
    # Normalize to 0-360
    return (bearing + 360) % 360


def get_cardinal_direction(bearing: float) -> str:
    """
    Get cardinal direction from bearing.
    
    Args:
        bearing: Bearing in degrees
    
    Returns:
        Cardinal direction (N, NE, E, SE, S, SW, W, NW)
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * \
        math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp to human-readable string.
    
    Args:
        timestamp: Datetime object
    
    Returns:
        Formatted timestamp string
    """
    now = datetime.now()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M")


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string.
    
    Args:
        json_str: JSON string
        default: Default value if parsing fails
    
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def dict_to_readable(d: Dict[str, Any], indent: int = 0) -> str:
    """
    Convert dictionary to readable string.
    
    Args:
        d: Dictionary to convert
        indent: Indentation level
    
    Returns:
        Readable string representation
    """
    lines = []
    indent_str = ' ' * indent
    
    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(dict_to_readable(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{indent_str}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{indent_str}  -")
                    lines.append(dict_to_readable(item, indent + 4))
                else:
                    lines.append(f"{indent_str}  - {item}")
        else:
            lines.append(f"{indent_str}{key}: {value}")
    
    return '\n'.join(lines)


def get_sri_lanka_timezone() -> str:
    """Get Sri Lanka timezone."""
    return "Asia/Colombo"


def is_business_hours(timestamp: datetime = None) -> bool:
    """
    Check if current time is during business hours in Sri Lanka.
    
    Args:
        timestamp: Datetime to check (defaults to now)
    
    Returns:
        True if during business hours (8 AM - 6 PM, Monday-Friday)
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    # Sri Lanka business hours: 8 AM to 6 PM, Monday to Friday
    return (
        timestamp.weekday() < 5 and  # Monday to Friday
        8 <= timestamp.hour < 18      # 8 AM to 6 PM
    )


def estimate_traffic_factor(timestamp: datetime = None) -> float:
    """
    Estimate traffic factor based on time of day in Sri Lanka.
    
    Args:
        timestamp: Datetime to check (defaults to now)
    
    Returns:
        Traffic factor (1.0 = normal, >1.0 = heavier traffic)
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    hour = timestamp.hour
    
    # Typical Sri Lanka traffic patterns
    if 7 <= hour < 9:          # Morning rush hour
        return 1.8
    elif 12 <= hour < 14:      # Lunch time
        return 1.3
    elif 16 <= hour < 19:      # Evening rush hour
        return 2.0
    elif 9 <= hour < 12:       # Mid-morning
        return 1.2
    elif 14 <= hour < 16:      # Mid-afternoon
        return 1.2
    elif 19 <= hour < 21:      # Evening
        return 1.4
    else:                      # Night/Overnight
        return 0.8