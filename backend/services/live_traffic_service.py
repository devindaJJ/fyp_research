import os
import requests
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def get_live_travel_time(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Get live travel time from Google Distance Matrix API
    Returns travel time in seconds
    """

    params = {
        "origins": f"{origin_lat},{origin_lng}",
        "destinations": f"{dest_lat},{dest_lng}",
        "departure_time": "now",
        "key": API_KEY
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print("API request failed")
        return None

    data = response.json()

    try:
        duration = data["rows"][0]["elements"][0]["duration_in_traffic"]["value"]
        return duration

    except KeyError:
        print("No traffic data available")
        return None