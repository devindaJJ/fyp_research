import React from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require("leaflet/dist/images/marker-icon-2x.png"),
  iconUrl: require("leaflet/dist/images/marker-icon.png"),
  shadowUrl: require("leaflet/dist/images/marker-shadow.png"),
});

const createIncidentIcon = (color) =>
  new L.DivIcon({
    html: `
      <div style="
        background:${color};
        width:18px;
        height:18px;
        border-radius:50%;
        border:3px solid white;
        box-shadow:0 0 6px rgba(0,0,0,0.35);
      "></div>
    `,
    className: "",
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });

const getIncidentColor = (type) => {
  switch ((type || "").toLowerCase()) {
    case "accident":
      return "#e53935";
    case "construction":
      return "#fb8c00";
    case "road_closure":
      return "#8e24aa";
    case "flooding":
      return "#1e88e5";
    case "pothole":
      return "#6d4c41";
    case "congestion_hotspot":
      return "#fdd835";
    default:
      return "#757575";
  }
};

const RouteMap = ({ analysis, selectedRouteIndex, incidents = [] }) => {
  if (!analysis || !analysis.primary_route || !analysis.primary_route.coordinates?.length) {
    return null;
  }

  const allRoutes = [analysis.primary_route, ...(analysis.alternatives || [])];

  const actualOrigin = analysis.origin_coords
    ? [analysis.origin_coords.lat, analysis.origin_coords.lng]
    : analysis.primary_route.coordinates[0];

  const actualDestination = analysis.destination_coords
    ? [analysis.destination_coords.lat, analysis.destination_coords.lng]
    : analysis.primary_route.coordinates[analysis.primary_route.coordinates.length - 1];

  return (
    <div className="map-wrapper">
      <h3 className="map-title">🗺 Route Map</h3>

      <MapContainer
        center={actualOrigin}
        zoom={13}
        scrollWheelZoom={true}
        className="route-map"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {allRoutes.map((route, index) => (
          <Polyline
            key={`route-${index}`}
            positions={route.coordinates}
            pathOptions={{
              color: index === selectedRouteIndex ? "#1565c0" : "#9e9e9e",
              weight: index === selectedRouteIndex ? 7 : 4,
              opacity: index === selectedRouteIndex ? 0.95 : 0.55,
              dashArray: index === selectedRouteIndex ? null : "10 8",
            }}
          />
        ))}

        <Marker position={actualOrigin}>
          <Popup>Start Location</Popup>
        </Marker>

        <Marker position={actualDestination}>
          <Popup>Destination</Popup>
        </Marker>

        {incidents.map((incident) => (
          <Marker
            key={`incident-${incident.incident_id}`}
            position={[parseFloat(incident.lat), parseFloat(incident.lng)]}
            icon={createIncidentIcon(getIncidentColor(incident.type))}
          >
            <Popup>
              <div>
                <strong>{String(incident.type || "").replace("_", " ").toUpperCase()}</strong>
                <br />
                Severity: {incident.severity}
                <br />
                {incident.description || "No description"}
                <br />
                <small>
                  Reported:{" "}
                  {incident.timestamp
                    ? new Date(incident.timestamp).toLocaleString()
                    : "Unknown time"}
                </small>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};

export default RouteMap;