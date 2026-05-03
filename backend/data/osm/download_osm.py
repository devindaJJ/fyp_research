import osmnx as ox
import os

# Make sure the save path exists
save_path = os.path.join(os.path.dirname(__file__), "sri_lanka_drive.graphml")

print("Downloading road network for Sri Lanka...")

# Download drivable roads only
graph = ox.graph_from_place("Sri Lanka", network_type="drive")

print("Download complete.")

# Save graph in the same folder
ox.save_graphml(graph, save_path)

print(f"Graph saved as {save_path}")