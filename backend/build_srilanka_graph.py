import os
import osmnx as ox

OUTPUT_DIR = "data/osm"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sri_lanka_drive.graphml")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Downloading Sri Lanka driving network from OpenStreetMap...")
    G = ox.graph_from_place("Sri Lanka", network_type="drive")

    print("Adding speed estimates...")
    G = ox.add_edge_speeds(G)

    print("Adding travel times...")
    G = ox.add_edge_travel_times(G)

    print("Saving graph...")
    ox.save_graphml(G, OUTPUT_FILE)

    print("Done.")
    print("Saved to:", OUTPUT_FILE)
    print("Nodes:", len(G.nodes))
    print("Edges:", len(G.edges))

if __name__ == "__main__":
    main()