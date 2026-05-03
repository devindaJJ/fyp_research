import osmnx as ox
import pandas as pd
import os

# Paths
graph_path = os.path.join(os.path.dirname(__file__), "../data/osm/sri_lanka_drive.graphml")
save_path = os.path.join(os.path.dirname(__file__), "../data/processed/sri_lanka_edges.csv")

print("Loading graph...")
G = ox.load_graphml(graph_path)

print("Extracting road segments...")
edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

# Reset index to turn 'u', 'v', 'key' from index into columns
edges = edges.reset_index()

print("Columns available in edges:", edges.columns)

# Select relevant columns
edges_df = edges[['u', 'v', 'length', 'highway', 'geometry']]

print(f"Saving edges to CSV: {save_path}")
os.makedirs(os.path.dirname(save_path), exist_ok=True)
edges_df.to_csv(save_path, index=False)

print("Done! Road segments ready for traffic analysis.")