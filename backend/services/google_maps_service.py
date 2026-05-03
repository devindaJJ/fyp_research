import os
import pandas as pd
import googlemaps
from dotenv import load_dotenv
from shapely.geometry import LineString
import osmnx as ox

# Load API key
load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)

# Paths
graph_path = os.path.join(os.path.dirname(__file__), "../data/processed/colombo_network_edges.csv")
save_path = os.path.join(os.path.dirname(__file__), "../data/processed/colombo_network_edges_with_time.csv")

# -------------------------------------------------
# STEP 0: Load Colombo district road network
# -------------------------------------------------
print("Downloading Colombo district road network...")

# Graph from Colombo district
G = ox.graph_from_place("Colombo, Sri Lanka", network_type="drive")

# Convert to GeoDataFrame
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
edges = edges.reset_index()

# Keep expressways + major city roads
edges = edges[edges['highway'].isin(['motorway', 'trunk', 'primary', 'secondary'])]

# Keep necessary columns
edges = edges[['u', 'v', 'length', 'highway', 'geometry']]

# Save CSV for reference
os.makedirs(os.path.dirname(graph_path), exist_ok=True)
edges.to_csv(graph_path, index=False)
print(f"Saved Colombo network edges CSV: {graph_path}")

# -------------------------------------------------
# STEP 1: Query Google Maps API for travel times
# -------------------------------------------------
edges = pd.read_csv(graph_path)

def get_midpoint_coords(geom_str):
    """Get midpoint of LINESTRING geometry"""
    line = LineString(eval(geom_str))
    mid = line.interpolate(0.5, normalized=True)
    return mid.y, mid.x  # lat, lon

# Use cached results if available
if os.path.exists(save_path):
    cached = pd.read_csv(save_path)
    print("Loaded cached travel times")
    edges['travel_time_sec'] = cached['travel_time_sec']
else:
    travel_times = []
    print("Querying Google Maps for Colombo network travel times...")
    for idx, row in edges.iterrows():
        try:
            lat, lng = get_midpoint_coords(row['geometry'])
            directions = gmaps.directions(
                origin=(lat, lng),
                destination=(lat, lng),
                mode="driving",
                departure_time="now"
            )
            duration = directions[0]['legs'][0]['duration']['value']
            travel_times.append(duration)
        except Exception as e:
            print(f"Error at row {idx}: {e}")
            travel_times.append(None)
    edges['travel_time_sec'] = travel_times
    edges.to_csv(save_path, index=False)
    print(f"Saved travel times CSV: {save_path}")

print("Done! Colombo network ready for congestion analysis.")