import React, { useEffect, useState } from "react";
import "./TrafficAnalyzer.css";
import RouteMap from "./RouteMap";

const TrafficAnalyzer = () => {
  const [destination, setDestination] = useState("");
  const [origin, setOrigin] = useState("");
  const [vehicleType, setVehicleType] = useState("car");

  const [useAutoLocation, setUseAutoLocation] = useState(true);
  const [loading, setLoading] = useState(false);
  const [loadingAlternatives, setLoadingAlternatives] = useState(false);
  const [reportingIncident, setReportingIncident] = useState(false);

  const [currentLocation, setCurrentLocation] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);
  const [error, setError] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [incidentMessage, setIncidentMessage] = useState("");

  const [incidentType, setIncidentType] = useState("accident");
  const [incidentSeverity, setIncidentSeverity] = useState("medium");
  const [incidentDescription, setIncidentDescription] = useState("");
  const [useCurrentIncidentLocation, setUseCurrentIncidentLocation] = useState(true);
  const [incidentLocationInput, setIncidentLocationInput] = useState("");

  const API_BASE_URL = "http://127.0.0.1:8000";

  const fetchIncidents = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/incidents`);
      const data = await response.json();

      if (data.success) {
        setIncidents(data.incidents || []);
      }
    } catch (err) {
      console.error("Failed to load incidents:", err);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const reverseGeocode = async (lat, lng) => {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=jsonv2`;

    const response = await fetch(url, {
      headers: { "Accept-Language": "en" },
    });

    const data = await response.json();

    if (!data || !data.display_name) {
      return {
        city: "Current Location",
        country: "Sri Lanka",
        address: `${lat}, ${lng}`,
      };
    }

    const address = data.address || {};

    return {
      city:
        address.city ||
        address.town ||
        address.village ||
        address.suburb ||
        "Current Location",
      country: address.country || "Sri Lanka",
      address: data.display_name,
    };
  };

  const geocodeAddress = async (address) => {
    const query = address.toLowerCase().includes("sri lanka")
      ? address
      : `${address}, Sri Lanka`;

    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
      query
    )}&format=jsonv2&limit=1`;

    const response = await fetch(url, {
      headers: { "Accept-Language": "en" },
    });

    const data = await response.json();

    if (!data || data.length === 0) {
      throw new Error("Location not found");
    }

    return {
      lat: parseFloat(data[0].lat),
      lng: parseFloat(data[0].lon),
      displayName: data[0].display_name,
    };
  };

  const fetchCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported by browser");
      return;
    }

    setLoading(true);
    setError(null);
    setIncidentMessage("");

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const locationInfo = await reverseGeocode(lat, lng);

          setCurrentLocation({
            lat,
            lng,
            city: locationInfo.city,
            country: locationInfo.country,
            address: locationInfo.address,
          });
        } catch {
          setCurrentLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            city: "Current Location",
            country: "Sri Lanka",
            address: `${position.coords.latitude}, ${position.coords.longitude}`,
          });
        }

        setLoading(false);
      },
      () => {
        setError("Unable to retrieve your location");
        setLoading(false);
      }
    );
  };

  const reportIncident = async () => {
    try {
      setError(null);
      setIncidentMessage("");

      if (!incidentDescription.trim()) {
        throw new Error("Please enter an incident description.");
      }

      let incidentLat;
      let incidentLng;

      if (useCurrentIncidentLocation) {
        if (!currentLocation) {
          throw new Error("Please detect your current location first.");
        }

        incidentLat = currentLocation.lat;
        incidentLng = currentLocation.lng;
      } else {
        if (!incidentLocationInput.trim()) {
          throw new Error("Please enter an incident location.");
        }

        const incidentGeo = await geocodeAddress(incidentLocationInput.trim());
        incidentLat = incidentGeo.lat;
        incidentLng = incidentGeo.lng;
      }

      setReportingIncident(true);

      const requestBody = {
        type: incidentType,
        severity: incidentSeverity,
        lat: incidentLat,
        lng: incidentLng,
        description: incidentDescription.trim(),
      };

      const response = await fetch(`${API_BASE_URL}/api/incidents/report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (data.success) {
        setIncidentMessage("Incident reported successfully.");
        setIncidentDescription("");
        setIncidentLocationInput("");
        await fetchIncidents();
      } else {
        throw new Error(data.error || "Failed to report incident.");
      }
    } catch (err) {
      setError(err.message || "Failed to report incident.");
    } finally {
      setReportingIncident(false);
    }
  };

  const loadAlternatives = async (requestBody) => {
    try {
      setLoadingAlternatives(true);

      const response = await fetch(
        `${API_BASE_URL}/api/traffic/alternative-routes`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        }
      );

      const data = await response.json();

      if (data.success) {
        setAnalysis((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            recommendation: {
              should_reroute: data.alternatives && data.alternatives.length > 0,
              alternative:
                data.alternatives && data.alternatives.length > 0
                  ? data.alternatives[0]
                  : null,
            },
            alternatives: data.alternatives || [],
          };
        });
      }
    } catch (err) {
      console.error("Alternative routes failed:", err);
    } finally {
      setLoadingAlternatives(false);
    }
  };

  const analyzeRoute = async () => {
    if (!destination.trim()) {
      setError("Please enter a destination");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setIncidentMessage("");
      setAnalysis(null);
      setSelectedRouteIndex(0);

      let originCoords;
      let originName;

      if (useAutoLocation && currentLocation) {
        originCoords = {
          lat: currentLocation.lat,
          lng: currentLocation.lng,
        };
        originName = currentLocation.address;
      } else {
        const originQuery = origin.trim();

        if (!originQuery) {
          throw new Error(
            "Please enter a starting point or use automatic location detection."
          );
        }

        const originGeo = await geocodeAddress(originQuery);
        originCoords = {
          lat: originGeo.lat,
          lng: originGeo.lng,
        };
        originName = originGeo.displayName;
      }

      const destGeo = await geocodeAddress(destination);
      const destCoords = {
        lat: destGeo.lat,
        lng: destGeo.lng,
      };

      const requestBody = {
        origin_lat: originCoords.lat,
        origin_lng: originCoords.lng,
        dest_lat: destCoords.lat,
        dest_lng: destCoords.lng,
        vehicle_type: vehicleType,
        origin_name: originName,
        destination_name: destGeo.displayName,
      };

      const response = await fetch(`${API_BASE_URL}/api/traffic/analyze-route`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (data.success) {
        setAnalysis(data.analysis);
        await fetchIncidents();

        if (!data.analysis.long_distance_mode) {
          loadAlternatives(requestBody);
        }
      } else {
        setError(data.error || "Failed to analyze route");
      }
    } catch (err) {
      setError(err.message || "Network error");
    } finally {
      setLoading(false);
    }
  };

  const getTrafficColor = (level) => {
    switch (level) {
      case "light":
        return "#4caf50";
      case "moderate":
        return "#ff9800";
      case "heavy":
        return "#f44336";
      default:
        return "#9e9e9e";
    }
  };

  const getTrafficIcon = (level) => {
    switch (level) {
      case "light":
        return "🟢";
      case "moderate":
        return "🟡";
      case "heavy":
        return "🔴";
      default:
        return "⚪";
    }
  };

  const getSelectedRoute = () => {
    if (!analysis) return null;
    if (selectedRouteIndex === 0) return analysis.primary_route;
    return analysis.alternatives[selectedRouteIndex - 1];
  };

  const selectedRoute = getSelectedRoute();

  return (
    <div className="traffic-analyzer">
      <div className="traffic-header">
        <h2>🚗 Traffic Route Analyzer</h2>
        <p>Adaptive Route Analysis</p>
      </div>

      <div className="location-section">
        <button onClick={fetchCurrentLocation} className="location-btn" disabled={loading}>
          📍 {currentLocation ? "Refresh Location" : "Detect My Location"}
        </button>

        {currentLocation && (
          <div className="current-location">
            <strong>Your Location:</strong> {currentLocation.city}, {currentLocation.country}
            <br />
            <small>{currentLocation.address}</small>
          </div>
        )}
      </div>

      <div className="route-form">
        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={useAutoLocation}
              onChange={(e) => setUseAutoLocation(e.target.checked)}
            />
            Use automatic location detection
          </label>
        </div>

        {!useAutoLocation && (
          <div className="form-group">
            <label>Starting Point</label>
            <input
              type="text"
              placeholder="e.g., Colombo Fort"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="route-input"
            />
          </div>
        )}

        <div className="form-group">
          <label>Destination *</label>
          <input
            type="text"
            placeholder="e.g., Maharagama"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            className="route-input"
          />
        </div>

        <div className="vehicle-section">
          <label className="vehicle-label">Select Vehicle</label>

          <div className="vehicle-buttons">
            <button
              className={vehicleType === "car" ? "vehicle-btn active" : "vehicle-btn"}
              onClick={() => setVehicleType("car")}
              type="button"
            >
              🚗 Car / Van
            </button>

            <button
              className={vehicleType === "bike" ? "vehicle-btn active" : "vehicle-btn"}
              onClick={() => setVehicleType("bike")}
              type="button"
            >
              🏍 Bike
            </button>

            <button
              className={
                vehicleType === "three_wheeler" ? "vehicle-btn active" : "vehicle-btn"
              }
              onClick={() => setVehicleType("three_wheeler")}
              type="button"
            >
              🛺 Three Wheel
            </button>

            <button
              className={vehicleType === "bus" ? "vehicle-btn active" : "vehicle-btn"}
              onClick={() => setVehicleType("bus")}
              type="button"
            >
              🚌 Bus / Lorry
            </button>
          </div>
        </div>

        <button
          onClick={analyzeRoute}
          className="analyze-btn"
          disabled={loading || !destination.trim()}
        >
          {loading ? "🔄 Analyzing..." : "🔍 Analyze Route"}
        </button>
      </div>

      <div className="route-form">
        <h3>🚨 Report Incident</h3>

        <div className="form-group">
          <label>Incident Type</label>
          <select
            value={incidentType}
            onChange={(e) => setIncidentType(e.target.value)}
            className="route-input"
          >
            <option value="accident">Accident</option>
            <option value="construction">Construction</option>
            <option value="road_closure">Road Closure</option>
            <option value="flooding">Flooding</option>
            <option value="pothole">Pothole</option>
            <option value="congestion_hotspot">Congestion Hotspot</option>
          </select>
        </div>

        <div className="form-group">
          <label>Severity</label>
          <select
            value={incidentSeverity}
            onChange={(e) => setIncidentSeverity(e.target.value)}
            className="route-input"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            placeholder="e.g., Major accident blocking one lane"
            value={incidentDescription}
            onChange={(e) => setIncidentDescription(e.target.value)}
            className="route-input"
          />
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={useCurrentIncidentLocation}
              onChange={(e) => setUseCurrentIncidentLocation(e.target.checked)}
            />
            Use my current location for incident
          </label>
        </div>

        {!useCurrentIncidentLocation && (
          <div className="form-group">
            <label>Incident Location</label>
            <input
              type="text"
              placeholder="e.g., Borella"
              value={incidentLocationInput}
              onChange={(e) => setIncidentLocationInput(e.target.value)}
              className="route-input"
            />
          </div>
        )}

        <button
          onClick={reportIncident}
          className="analyze-btn"
          disabled={reportingIncident}
          type="button"
        >
          {reportingIncident ? "⏳ Reporting..." : "📢 Report Incident"}
        </button>

        {useCurrentIncidentLocation && !currentLocation && (
          <div className="estimate-note">
            * Detect your location first if you want to report using your current location.
          </div>
        )}

        {incidentMessage && (
          <div className="success-message">
            ✅ {incidentMessage}
          </div>
        )}
      </div>

      {error && <div className="error-message">⚠️ {error}</div>}

      {analysis && selectedRoute && (
        <>
          <div className="analysis-results">
            <div className="route-header">
              <h3>📍 Route Analysis</h3>
              <span className="analysis-time">
                {analysis.analysis_time
                  ? new Date(analysis.analysis_time).toLocaleString()
                  : ""}
              </span>
            </div>

            <div className="route-info">
              <div className="route-point">
                <strong>From:</strong> {analysis.origin}
              </div>

              <div className="route-point">
                <strong>To:</strong> {analysis.destination}
              </div>
            </div>

            <div
              className="traffic-card primary-route"
              style={{
                borderColor:
                  selectedRouteIndex === 0
                    ? getTrafficColor(analysis.congestion.level)
                    : getTrafficColor(selectedRoute.traffic_level),
              }}
            >
              <div className="card-header">
                <h4>
                  {selectedRouteIndex === 0
                    ? getTrafficIcon(analysis.congestion.level)
                    : getTrafficIcon(selectedRoute.traffic_level)}{" "}
                  Estimated Conditions
                </h4>

                <span
                  className="traffic-badge"
                  style={{
                    backgroundColor:
                      selectedRouteIndex === 0
                        ? getTrafficColor(analysis.congestion.level)
                        : getTrafficColor(selectedRoute.traffic_level),
                  }}
                >
                  {selectedRouteIndex === 0
                    ? analysis.congestion.level.toUpperCase()
                    : selectedRoute.traffic_level.toUpperCase()}
                </span>
              </div>

              <div className="traffic-details">
                <div className="detail-row">
                  <span className="label">Distance:</span>
                  <span className="value">{selectedRoute.distance_text}</span>
                </div>

                <div className="detail-row">
                  <span className="label">Normal Time:</span>
                  <span className="value">
                    {Math.round(selectedRoute.normal_duration)} min
                  </span>
                </div>

                <div className="detail-row">
                  <span className="label">Estimated Time:</span>
                  <span className="value highlight">
                    {Math.round(selectedRoute.traffic_duration)} min
                  </span>
                </div>
              </div>
            </div>

            <div className="alternatives-section">
              <h4>🛣 Available Routes</h4>

              {loadingAlternatives && (
                <div className="loading-alt-message">Loading alternative routes...</div>
              )}

              <div className="alternatives-grid">
                <div
                  className={`alternative-card ${
                    selectedRouteIndex === 0 ? "selected-route-card" : ""
                  }`}
                  onClick={() => setSelectedRouteIndex(0)}
                >
                  <div className="alt-header">
                    <span className="alt-number">Route 1</span>
                    <span
                      className="alt-badge"
                      style={{ backgroundColor: getTrafficColor(analysis.congestion.level) }}
                    >
                      {getTrafficIcon(analysis.congestion.level)}
                    </span>
                  </div>

                  <p className="alt-summary">Primary route</p>

                  <div className="alt-details">
                    <div>⏱️ {Math.round(analysis.primary_route.traffic_duration)} min</div>
                    <div>📏 {analysis.primary_route.distance_text}</div>
                  </div>
                </div>

                {analysis.alternatives &&
                  analysis.alternatives.map((alt, index) => (
                    <div
                      key={index}
                      className={`alternative-card ${
                        selectedRouteIndex === index + 1 ? "selected-route-card" : ""
                      }`}
                      onClick={() => setSelectedRouteIndex(index + 1)}
                    >
                      <div className="alt-header">
                        <span className="alt-number">Route {index + 2}</span>
                        <span
                          className="alt-badge"
                          style={{ backgroundColor: getTrafficColor(alt.traffic_level) }}
                        >
                          {getTrafficIcon(alt.traffic_level)}
                        </span>
                      </div>

                      <p className="alt-summary">Alternative route</p>

                      <div className="alt-details">
                        <div>⏱️ {Math.round(alt.traffic_duration)} min</div>
                        <div>📏 {alt.distance_text}</div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          <RouteMap
            analysis={analysis}
            selectedRouteIndex={selectedRouteIndex}
            incidents={incidents}
          />
        </>
      )}
    </div>
  );
};

export default TrafficAnalyzer;