import csv
import datetime
import os
import time
import pandas as pd

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from services.rerouting_engine import (
    load_graph,
    load_edges_dataset,
    load_incidents,
    build_routing_graph,
    apply_incident_penalties,
    find_nearest_node_with_distance,
    calculate_shortest_path,
    calculate_multiple_routes,
    get_route_coordinates,
    get_corridor_subgraph,
    filter_edges_for_subgraph,
    get_route_summary,
    haversine_distance
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_GRAPH = load_graph()
EDGES_DF = load_edges_dataset()

INCIDENTS_FILE = os.path.join("data", "incidents", "manual_incidents.csv")


class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    dest_lat: float
    dest_lng: float
    vehicle_type: str
    origin_name: str | None = None
    destination_name: str | None = None


class IncidentReportRequest(BaseModel):
    type: str
    severity: str
    lat: float
    lng: float
    description: str = ""


@app.get("/")
def home():
    return {"message": "Sri Lanka Incident-Aware Routing API is running"}


def save_incident_report(report: IncidentReportRequest):
    os.makedirs(os.path.dirname(INCIDENTS_FILE), exist_ok=True)

    # determine next incident id
    next_id = 1

    if os.path.exists(INCIDENTS_FILE):
        try:
            df = pd.read_csv(INCIDENTS_FILE)

            if not df.empty and "incident_id" in df.columns:
                next_id = int(df["incident_id"].max()) + 1

        except Exception:
            next_id = 1

    file_exists = os.path.exists(INCIDENTS_FILE)

    with open(INCIDENTS_FILE, "a", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "incident_id",
                "type",
                "severity",
                "lat",
                "lng",
                "status",
                "description",
                "timestamp"
            ])

        writer.writerow([
            next_id,
            report.type,
            report.severity,
            report.lat,
            report.lng,
            "active",
            report.description,
            datetime.datetime.now().isoformat()
        ])


def build_graph_for_request(request: RouteRequest):
    straight_distance_m = haversine_distance(
        request.origin_lat,
        request.origin_lng,
        request.dest_lat,
        request.dest_lng
    )

    long_distance_mode = straight_distance_m > 30000

    if long_distance_mode:
        buffer_deg = 0.12
        max_route_points = 80
    else:
        buffer_deg = 0.08
        max_route_points = 120

    sub_base_graph = get_corridor_subgraph(
        BASE_GRAPH,
        request.origin_lat,
        request.origin_lng,
        request.dest_lat,
        request.dest_lng,
        buffer_deg=buffer_deg
    )

    sub_edges_df = filter_edges_for_subgraph(EDGES_DF, sub_base_graph)
    current_hour = datetime.datetime.now().hour

    routing_graph = build_routing_graph(
        sub_base_graph,
        sub_edges_df,
        request.vehicle_type,
        current_hour
    )

    # load and apply incidents
    incidents_df = load_incidents()
    active_incident_count = apply_incident_penalties(routing_graph, incidents_df)

    return routing_graph, long_distance_mode, max_route_points, active_incident_count


@app.get("/api/incidents")
def get_active_incidents():
    incidents_df = load_incidents()

    return {
        "success": True,
        "count": len(incidents_df),
        "incidents": incidents_df.to_dict(orient="records")
    }


@app.post("/api/incidents/report")
def report_incident(report: IncidentReportRequest):
    save_incident_report(report)

    return {
        "success": True,
        "message": "Incident report saved successfully."
    }


@app.post("/api/traffic/analyze-route")
def analyze_route(request: RouteRequest):
    routing_graph, long_distance_mode, max_route_points, active_incident_count = build_graph_for_request(request)

    print("Primary route request")
    print("Long distance mode:", long_distance_mode)
    print("Graph nodes:", len(routing_graph.nodes))
    print("Graph edges:", len(routing_graph.edges))
    print("Active incidents affecting graph:", active_incident_count)

    start_node, start_snap_distance = find_nearest_node_with_distance(
        routing_graph, request.origin_lat, request.origin_lng
    )
    end_node, end_snap_distance = find_nearest_node_with_distance(
        routing_graph, request.dest_lat, request.dest_lng
    )

    print("Origin:", request.origin_name, request.origin_lat, request.origin_lng)
    print("Destination:", request.destination_name, request.dest_lat, request.dest_lng)
    print("Start snap distance (m):", start_snap_distance)
    print("End snap distance (m):", end_snap_distance)

    MAX_SNAP_DISTANCE_METERS = 5000

    if start_snap_distance > MAX_SNAP_DISTANCE_METERS:
        return {
            "success": False,
            "error": "The starting point is too far from a mapped road in the Sri Lanka road network."
        }

    if end_snap_distance > MAX_SNAP_DISTANCE_METERS:
        return {
            "success": False,
            "error": "The destination is too far from a mapped road in the Sri Lanka road network."
        }

    primary_path, primary_time_sec, primary_distance_m, primary_free_flow_sec = calculate_shortest_path(
        routing_graph,
        start_node,
        end_node
    )

    if not primary_path:
        return {
            "success": False,
            "error": "No route could be found between these locations."
        }

    primary_distance_km = round(primary_distance_m / 1000, 2)
    primary_time_min = round(primary_time_sec / 60, 2)
    normal_duration = round(primary_free_flow_sec / 60, 2)

    primary_coords = get_route_coordinates(
        routing_graph,
        primary_path,
        max_points=max_route_points
    )

    delay_minutes = max(0, round(primary_time_min - normal_duration, 2))

    if delay_minutes < 5:
        congestion_level = "light"
    elif delay_minutes < 15:
        congestion_level = "moderate"
    else:
        congestion_level = "heavy"

    delay_percentage = round(
        ((delay_minutes / normal_duration) * 100) if normal_duration > 0 else 0,
        2
    )

    return {
        "success": True,
        "analysis": {
            "origin": request.origin_name or "Current Location",
            "destination": request.destination_name or "Destination",
            "vehicle_type": request.vehicle_type,
            "analysis_time": datetime.datetime.now().isoformat(),
            "routing_source": "sri_lanka_incident_aware_engine",
            "long_distance_mode": long_distance_mode,

            "incident_info": {
                "active_incident_count": active_incident_count
            },

            "origin_coords": {
                "lat": request.origin_lat,
                "lng": request.origin_lng
            },
            "destination_coords": {
                "lat": request.dest_lat,
                "lng": request.dest_lng
            },

            "congestion": {
                "level": congestion_level
            },

            "primary_route": {
                "distance_text": f"{primary_distance_km} km",
                "normal_duration": normal_duration,
                "traffic_duration": primary_time_min,
                "delay_minutes": delay_minutes,
                "delay_percentage": delay_percentage,
                "summary": get_route_summary(routing_graph, primary_path),
                "coordinates": primary_coords
            },

            "recommendation": {
                "should_reroute": False,
                "alternative": None
            },

            "alternatives": []
        }
    }


@app.post("/api/traffic/alternative-routes")
def alternative_routes(request: RouteRequest):
    routing_graph, long_distance_mode, max_route_points, active_incident_count = build_graph_for_request(request)

    if long_distance_mode:
        return {
            "success": True,
            "incident_info": {
                "active_incident_count": active_incident_count
            },
            "alternatives": []
        }

    print("Alternative routes request")
    print("Active incidents affecting graph:", active_incident_count)

    start_node, _ = find_nearest_node_with_distance(
        routing_graph, request.origin_lat, request.origin_lng
    )
    end_node, _ = find_nearest_node_with_distance(
        routing_graph, request.dest_lat, request.dest_lng
    )

    raw_routes = calculate_multiple_routes(
        routing_graph,
        start_node,
        end_node,
        k=2
    )

    alternatives = []

    for route in raw_routes[1:]:
        distance_km = round(route["distance_m"] / 1000, 2)
        alt_normal_min = round(route["free_flow_time_sec"] / 60, 2)
        time_min = round(route["travel_time_sec"] / 60, 2)
        alt_delay = max(0, round(time_min - alt_normal_min, 2))

        if alt_delay < 5:
            alt_level = "light"
        elif alt_delay < 15:
            alt_level = "moderate"
        else:
            alt_level = "heavy"

        alternatives.append({
            "summary": get_route_summary(routing_graph, route["path"]),
            "distance_text": f"{distance_km} km",
            "normal_duration": alt_normal_min,
            "traffic_duration": time_min,
            "delay_minutes": alt_delay,
            "delay_percentage": round(((alt_delay / alt_normal_min) * 100), 2) if alt_normal_min > 0 else 0,
            "traffic_level": alt_level,
            "coordinates": get_route_coordinates(
                routing_graph,
                route["path"],
                max_points=max_route_points
            )
        })

    return {
        "success": True,
        "incident_info": {
            "active_incident_count": active_incident_count
        },
        "alternatives": alternatives
    }