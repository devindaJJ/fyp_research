import os
import requests
import polyline
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def map_vehicle_mode(vehicle_type: str) -> str:
    vehicle_type = vehicle_type.lower()

    if vehicle_type in ["bike", "three_wheeler", "threewheel"]:
        return "TWO_WHEELER"

    # car / van / bus / lorry all go through DRIVE in standard Routes API
    return "DRIVE"


def map_congestion_level(delay_min: float) -> str:
    if delay_min < 3:
        return "light"
    elif delay_min < 10:
        return "moderate"
    return "heavy"


def decode_polyline(encoded: str):
    if not encoded:
        return []
    coords = polyline.decode(encoded)
    return [[lat, lng] for lat, lng in coords]


def compute_google_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    vehicle_type: str
):
    if not GOOGLE_MAPS_API_KEY:
        return {
            "success": False,
            "error": "GOOGLE_MAPS_API_KEY not found in environment."
        }

    travel_mode = map_vehicle_mode(vehicle_type)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": ",".join([
            "routes.distanceMeters",
            "routes.duration",
            "routes.staticDuration",
            "routes.polyline.encodedPolyline",
            "routes.routeLabels"
        ])
    }

    body = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": origin_lat,
                    "longitude": origin_lng
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": dest_lat,
                    "longitude": dest_lng
                }
            }
        },
        "travelMode": travel_mode,
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "computeAlternativeRoutes": True,
        "languageCode": "en-US",
        "units": "METRIC"
    }

    response = requests.post(ROUTES_URL, headers=headers, json=body, timeout=60)

    if response.status_code != 200:
        return {
            "success": False,
            "error": f"Google Routes API error: {response.status_code} - {response.text}"
        }

    data = response.json()
    routes = data.get("routes", [])

    if not routes:
        return {
            "success": False,
            "error": "No routes returned by Google Routes API."
        }

    parsed_routes = []

    for idx, route in enumerate(routes, start=1):
        distance_m = route.get("distanceMeters", 0)

        # duration and staticDuration come like "1234s"
        duration_raw = route.get("duration", "0s")
        static_raw = route.get("staticDuration", "0s")

        duration_sec = float(duration_raw.replace("s", ""))
        static_sec = float(static_raw.replace("s", ""))

        delay_min = max(0, round((duration_sec - static_sec) / 60, 2))

        parsed_routes.append({
            "summary": f"Route {idx}",
            "distance_text": f"{round(distance_m / 1000, 2)} km",
            "normal_duration": round(static_sec / 60, 2),
            "traffic_duration": round(duration_sec / 60, 2),
            "delay_minutes": delay_min,
            "delay_percentage": round(((duration_sec - static_sec) / static_sec * 100), 2) if static_sec > 0 else 0,
            "traffic_level": map_congestion_level(delay_min),
            "coordinates": decode_polyline(
                route.get("polyline", {}).get("encodedPolyline", "")
            ),
            "route_labels": route.get("routeLabels", [])
        })

    primary = parsed_routes[0]
    alternatives = parsed_routes[1:]

    return {
        "success": True,
        "primary_route": primary,
        "alternatives": alternatives
    }