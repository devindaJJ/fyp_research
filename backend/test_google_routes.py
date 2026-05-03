import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

if not API_KEY:
    print("GOOGLE_MAPS_API_KEY not found in .env")
    raise SystemExit

headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": API_KEY,
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
                "latitude": 6.8472783,
                "longitude": 79.9266082
            }
        }
    },
    "destination": {
        "location": {
            "latLng": {
                "latitude": 6.9148334,
                "longitude": 79.8776
            }
        }
    },
    "travelMode": "DRIVE",
    "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
    "computeAlternativeRoutes": True,
    "languageCode": "en-US",
    "units": "METRIC"
}

response = requests.post(ROUTES_URL, headers=headers, json=body, timeout=60)

print("Status code:", response.status_code)
print("Response text:")
print(response.text)