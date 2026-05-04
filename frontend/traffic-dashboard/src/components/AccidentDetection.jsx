import React, { useEffect, useState } from "react";

const API_URL = "http://localhost:8000/api";

function AccidentDetection() {
  // Fields match exactly what backend /api/accidents returns:
  // { date, latitude, longitude, vibration, distance }
  // These come from app.py accident_records list which stores lowercase keys internally
  const [accidentAlert, setAccidentAlert] = useState({
    detected: false,
    date: "",
    latitude: "",
    longitude: "",
    vibration: "",
    distance: ""
  });

  const [accidentHistory, setAccidentHistory] = useState([]);
  const [statistics, setStatistics] = useState({
    total: 0,
    vibrationYes: 0,
    vibrationNo: 0,
    latestDistance: 0
  });

  const fetchAccidents = async () => {
    try {
      console.log("🔄 Fetching accidents from:", `${API_URL}/accidents`);
      const response = await fetch(`${API_URL}/accidents`);
      const data = await response.json();
      
      console.log("✅ Response received:", { status: response.status, data });

      if (data.success) {
        const accidents = data.accidents || [];
        console.log(`📊 Got ${accidents.length} accident records`);

        const formattedHistory = accidents.map((acc) => ({
          date: acc.date || "",
          latitude: acc.latitude || acc.Latitude || "",
          longitude: acc.longitude || acc.Longitude || "",
          vibration: acc.vibration || acc.Vibration || "",
          distance: acc.distance || acc.Distance || 0
        }));

        setAccidentHistory(formattedHistory);

        // Count YES vs NO from Vibration column
        const vibrationYes = formattedHistory.filter(
          (x) => String(x.vibration).toUpperCase() === "YES"
        ).length;

        const vibrationNo = formattedHistory.filter(
          (x) => String(x.vibration).toUpperCase() !== "YES"
        ).length;

        // Latest record = last item in array (most recent sheet row)
        const latest = formattedHistory[formattedHistory.length - 1];

        setStatistics({
          total: formattedHistory.length,
          vibrationYes,
          vibrationNo,
          latestDistance: latest ? latest.distance : 0
        });

        // Show latest record in top alert banner
        if (latest) {
          console.log("🚨 Latest accident:", latest);
          setAccidentAlert({
            detected: true,
            date: latest.date,
            latitude: latest.latitude,
            longitude: latest.longitude,
            vibration: latest.vibration,
            distance: latest.distance
          });
        }
      } else {
        console.warn("❌ API response not successful:", data);
      }
    } catch (error) {
      console.error("💥 Error fetching accidents:", error);
    }
  };

  useEffect(() => {
    fetchAccidents();
    const interval = setInterval(fetchAccidents, 5000);
    return () => clearInterval(interval);
  }, []);

  // Red if vibration YES (impact), green if NO (normal)
  const alertColor =
    String(accidentAlert.vibration).toUpperCase() === "YES"
      ? "#f44336"
      : "#4caf50";

  return (
    <div
      style={{
        padding: "20px",
        fontFamily: "Arial, sans-serif",
        backgroundColor: "#f5f5f5",
        minHeight: "100vh"
      }}
    >
      {/* Top banner — shows latest accident_records entry */}
      {accidentAlert.detected && (
        <div
          style={{
            backgroundColor: alertColor,
            color: "#fff",
            padding: "15px",
            borderRadius: "6px",
            marginBottom: "20px",
            fontWeight: "bold",
            boxShadow: "0 4px 8px rgba(0,0,0,0.2)",
            animation:
              String(accidentAlert.vibration).toUpperCase() === "YES"
                ? "blink 1s infinite"
                : "none"
          }}
        >
          🚨 LATEST ACCIDENT RECORD
          <br />
          📅 Date: {accidentAlert.date}
          <br />
          📍 Latitude: {accidentAlert.latitude}
          <br />
          📍 Longitude: {accidentAlert.longitude}
          <br />
          💥 Vibration: {accidentAlert.vibration}
          <br />
          📏 Distance: {accidentAlert.distance} cm
        </div>
      )}

      <h2 style={{ marginBottom: "20px" }}>🚑 Accident Detection System</h2>

      {/* System Status */}
      <div
        style={{
          backgroundColor: "#fff",
          padding: "15px",
          borderRadius: "8px",
          marginBottom: "20px",
          boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
        }}
      >
        <h3>📊 System Status</h3>
        <div style={{ display: "flex", gap: "30px", flexWrap: "wrap" }}>
          <div>
            <strong>Total Records:</strong> {statistics.total}
          </div>
          <div>
            <strong>Vibration YES:</strong>{" "}
            <span style={{ color: "#f44336", fontWeight: "bold" }}>
              {statistics.vibrationYes}
            </span>
          </div>
          <div>
            <strong>Vibration NO:</strong>{" "}
            <span style={{ color: "#4caf50", fontWeight: "bold" }}>
              {statistics.vibrationNo}
            </span>
          </div>
          <div>
            <strong>Latest Distance:</strong> {statistics.latestDistance} cm
          </div>
        </div>
      </div>

      {/* Info cards */}
      <div
        style={{
          display: "flex",
          gap: "20px",
          flexWrap: "wrap",
          marginBottom: "40px"
        }}
      >
        {/* Latest Location */}
        <div
          style={{
            flex: "1",
            minWidth: "300px",
            backgroundColor: "#fff",
            borderRadius: "10px",
            padding: "20px",
            boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
          }}
        >
          <h3 style={{ textAlign: "center" }}>📍 Latest Location</h3>
          <p>
            <strong>Latitude:</strong>{" "}
            {accidentAlert.latitude || "No Data"}
          </p>
          <p>
            <strong>Longitude:</strong>{" "}
            {accidentAlert.longitude || "No Data"}
          </p>
          <p>
            <strong>Date:</strong>{" "}
            {accidentAlert.date || "No Data"}
          </p>
        </div>

        {/* Sensor Data */}
        <div
          style={{
            flex: "1",
            minWidth: "300px",
            backgroundColor: "#fff",
            borderRadius: "10px",
            padding: "20px",
            boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
          }}
        >
          <h3 style={{ textAlign: "center" }}>🚗 Sensor Data</h3>
          <p>
            <strong>Vibration:</strong>{" "}
            <span
              style={{
                color:
                  String(accidentAlert.vibration).toUpperCase() === "YES"
                    ? "red"
                    : "green",
                fontWeight: "bold"
              }}
            >
              {accidentAlert.vibration || "No Data"}
            </span>
          </p>
          <p>
            <strong>Distance:</strong>{" "}
            {accidentAlert.distance || "No Data"} cm
          </p>
          <p>
            <strong>Status:</strong>{" "}
            <span
              style={{
                color:
                  String(accidentAlert.vibration).toUpperCase() === "YES"
                    ? "red"
                    : "green",
                fontWeight: "bold"
              }}
            >
              {String(accidentAlert.vibration).toUpperCase() === "YES"
                ? "⚠️ Impact Detected"
                : "✅ Normal"}
            </span>
          </p>
        </div>
      </div>

      {/* Accident Records Table */}
      {/* Columns: date | latitude | longitude | vibration | distance */}
      {/* Match sheet headers: date | Latitude | Longitude | Vibration | Distance */}
      <div style={{ marginBottom: "40px" }}>
        <h3>🚗 Accident Records ({accidentHistory.length})</h3>

        {accidentHistory.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "left",
                backgroundColor: "#fff",
                boxShadow: "0 4px 8px rgba(0,0,0,0.2)"
              }}
            >
              <thead style={{ backgroundColor: "#f2f2f2" }}>
                <tr>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Latitude</th>
                  <th style={thStyle}>Longitude</th>
                  <th style={thStyle}>Vibration</th>
                  <th style={thStyle}>Distance (cm)</th>
                </tr>
              </thead>
              <tbody>
                {/* Newest records first */}
                {[...accidentHistory].reverse().map((acc, index) => (
                  <tr
                    key={index}
                    style={{
                      borderBottom: "1px solid #ddd",
                      // Highlight impact rows in light red
                      backgroundColor:
                        String(acc.vibration).toUpperCase() === "YES"
                          ? "#fff5f5"
                          : "#fff"
                    }}
                  >
                    {/* acc.date ← backend "date" ← sheet "date" */}
                    <td style={tdStyle}>{acc.date}</td>

                    {/* acc.latitude ← backend "latitude" ← sheet "Latitude" */}
                    <td style={tdStyle}>{acc.latitude}</td>

                    {/* acc.longitude ← backend "longitude" ← sheet "Longitude" */}
                    <td style={tdStyle}>{acc.longitude}</td>

                    {/* acc.vibration ← backend "vibration" ← sheet "Vibration" (YES/NO) */}
                    <td
                      style={{
                        ...tdStyle,
                        fontWeight: "bold",
                        color:
                          String(acc.vibration).toUpperCase() === "YES"
                            ? "red"
                            : "green"
                      }}
                    >
                      {acc.vibration}
                    </td>

                    {/* acc.distance ← backend "distance" ← sheet "Distance" */}
                    <td style={tdStyle}>{acc.distance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>No accident records found.</p>
        )}
      </div>

      <style>
        {`
          @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.4; }
            100% { opacity: 1; }
          }
        `}
      </style>
    </div>
  );
}

const thStyle = { padding: "12px", border: "1px solid #ddd" };
const tdStyle = { padding: "12px", border: "1px solid #ddd" };

export default AccidentDetection;