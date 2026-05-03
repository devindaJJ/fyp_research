# main.py
from fastapi import FastAPI, HTTPException
from services.rerouting_engine import load_graph, calculate_shortest_path

app = FastAPI(title="Colombo Traffic API")

# Load the graph once at startup
graph = load_graph()

@app.get("/")
def home():
    return {"message": "Traffic API is running"}

@app.get("/reroute")
def reroute(start_node: int, end_node: int):
    path, travel_time_min = calculate_shortest_path(graph, start_node, end_node)
    if not path:
        raise HTTPException(status_code=404, detail="No path found between nodes")
    return {
        "start_node": start_node,
        "end_node": end_node,
        "path": path,
        "estimated_travel_time_min": travel_time_min
    }