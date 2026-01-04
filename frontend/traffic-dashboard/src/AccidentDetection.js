import React, { useEffect, useState } from "react";

const API_URL = "http://localhost:8000/api";

function AccidentDetection() {
  const [accidentAlert, setAccidentAlert] = useState({
    detected: false,
    location: "",
    severity: "",
    time: "",
    distance: 0,
    totalImpacts: 0
  });

  const [accidentHistory, setAccidentHistory] = useState([]);
  const [statistics, setStatistics] = useState({
    total: 0,
    last24h: 0,
    activeAlerts: 0,
    connectedDevices: 0,
    mlActive: false
  });
  const [alerts, setAlerts] = useState([]);
  const [devices, setDevices] = useState([]);

  const [monthlyData, setMonthlyData] = useState({
    month: "January 2026",
    low: 0,
    medium: 0,
    high: 0,
    critical: 0
  });

  const radius = 70;
  const circumference = 2 * Math.PI * radius;

  const severityColors = {
    high: "#f44336",
    critical: "#d32f2f",
    medium: "#ff9800",
    low: "#4caf50"
  };

  const getAlertStyle = () => ({
    backgroundColor: severityColors[accidentAlert.severity] || "#ddd",
    color: ["low"].includes(accidentAlert.severity) ? "#000" : "#fff"
  });

  const blinkStyle = ["high", "critical"].includes(accidentAlert.severity)
    ? { animation: "blink 1s infinite" }
    : {};

  // Fetch accidents from backend
  const fetchAccidents = async () => {
    try {
      const response = await fetch(`${API_URL}/accidents?hours=24`);
      const data = await response.json();
      
      if (data.success) {
        const accidents = data.accidents;
        
        // Update history
        const formattedHistory = accidents.map(acc => ({
          severity: acc.severity,
          time: new Date(acc.timestamp).toLocaleTimeString(),
          location: acc.location,
          date: new Date(acc.timestamp),
          distance: acc.distance,
          totalImpacts: acc.total_impacts
        }));
        setAccidentHistory(formattedHistory);
        
        // Update monthly counts
        if (data.severity_counts) {
          setMonthlyData(prev => ({
            ...prev,
            low: data.severity_counts.low || 0,
            medium: data.severity_counts.medium || 0,
            high: data.severity_counts.high || 0,
            critical: data.severity_counts.critical || 0
          }));
        }
        
        // Update current alert with latest accident
        if (accidents.length > 0) {
          const latest = accidents[accidents.length - 1];
          setAccidentAlert({
            detected: true,
            location: latest.location,
            severity: latest.severity,
            time: new Date(latest.timestamp).toLocaleTimeString(),
            distance: latest.distance,
            totalImpacts: latest.total_impacts
          });
        }
      }
    } catch (error) {
      console.error("Error fetching accidents:", error);
    }
  };

  // Fetch alerts
  const fetchAlerts = async () => {
    try {
      const response = await fetch(`${API_URL}/alerts`);
      const data = await response.json();
      
      if (data.success) {
        setAlerts(data.alerts);
      }
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  };

  // Fetch statistics
  const fetchStatistics = async () => {
    try {
      const response = await fetch(`${API_URL}/statistics`);
      const data = await response.json();
      
      if (data.success) {
        setStatistics({
          total: data.statistics.total_accidents,
          last24h: data.statistics.accidents_last_24h,
          activeAlerts: data.statistics.active_alerts,
          connectedDevices: data.statistics.connected_devices,
          mlActive: data.statistics.ml_models_active
        });
      }
    } catch (error) {
      console.error("Error fetching statistics:", error);
    }
  };

  // Fetch devices
  const fetchDevices = async () => {
    try {
      const response = await fetch(`${API_URL}/devices`);
      const data = await response.json();
      
      if (data.success) {
        setDevices(data.devices);
      }
    } catch (error) {
      console.error("Error fetching devices:", error);
    }
  };

  // Initial load
  useEffect(() => {
    fetchAccidents();
    fetchAlerts();
    fetchStatistics();
    fetchDevices();
    
    // Refresh every 5 seconds
    const interval = setInterval(() => {
      fetchAccidents();
      fetchAlerts();
      fetchStatistics();
      fetchDevices();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  // Sound alerts
  useEffect(() => {
    if (!accidentAlert.detected) return;

    let soundUrl = "";
    switch (accidentAlert.severity) {
      case "high":
      case "critical":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg";
        break;
      case "medium":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg";
        break;
      case "low":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg";
        break;
      default:
        return;
    }

    const audio = new Audio(soundUrl);
    audio.play().catch(e => console.log("Audio play failed:", e));
  }, [accidentAlert]);

  const total = monthlyData.low + monthlyData.medium + monthlyData.high + monthlyData.critical;
  const lowPct = total > 0 ? (monthlyData.low / total) * 100 : 0;
  const mediumPct = total > 0 ? (monthlyData.medium / total) * 100 : 0;
  const highPct = total > 0 ? (monthlyData.high / total) * 100 : 0;
  const criticalPct = total > 0 ? (monthlyData.critical / total) * 100 : 0;

  const safetyStatus =
    monthlyData.critical > 5 ? "Critical" :
    monthlyData.high > 10 ? "Poor" :
    monthlyData.medium > 10 ? "Average" :
    "Good";

  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif", backgroundColor: "#f5f5f5", minHeight: "100vh" }}>
      {/* Top alert */}
      {accidentAlert.detected && (
        <div
          style={{
            ...getAlertStyle(),
            ...blinkStyle,
            padding: "15px",
            borderRadius: "6px",
            marginBottom: "20px",
            fontWeight: "bold",
            boxShadow: "0 4px 8px rgba(0,0,0,0.2)"
          }}
        >
          🚨 ACCIDENT ALERT ({accidentAlert.severity.toUpperCase()})
          <br />
          📍 Location: {accidentAlert.location}
          <br />
          ⏰ Time: {accidentAlert.time}
          <br />
          📏 Distance: {accidentAlert.distance}cm | 💥 Impacts: {accidentAlert.totalImpacts}
        </div>
      )}

      <h2 style={{ marginBottom: "20px" }}>🚑 ML-Powered Accident Detection System</h2>

      {/* System Status */}
      <div style={{
        backgroundColor: "#fff",
        padding: "15px",
        borderRadius: "8px",
        marginBottom: "20px",
        boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
      }}>
        <h3>📊 System Status</h3>
        <div style={{ display: "flex", gap: "30px", flexWrap: "wrap" }}>
          <div>
            <strong>Total Accidents:</strong> {statistics.total}
          </div>
          <div>
            <strong>Last 24h:</strong> {statistics.last24h}
          </div>
          <div>
            <strong>Active Alerts:</strong> {statistics.activeAlerts}
          </div>
          <div>
            <strong>Connected Devices:</strong> {statistics.connectedDevices}
          </div>
          <div>
            <strong>ML Models:</strong>{" "}
            <span style={{ color: statistics.mlActive ? "green" : "red" }}>
              {statistics.mlActive ? "✓ Active" : "✗ Inactive"}
            </span>
          </div>
        </div>
      </div>

      {/* Dashboard */}
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", marginBottom: "40px" }}>
        {/* Monthly Accident Rating */}
        <div style={{
          flex: "1",
          minWidth: "300px",
          backgroundColor: "#fff",
          borderRadius: "10px",
          padding: "20px",
          boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
        }}>
          <h3 style={{ textAlign: "center" }}>📊 Severity Distribution – {monthlyData.month}</h3>
          <div style={{ display: "flex", gap: "20px", alignItems: "center", justifyContent: "center" }}>
            <svg width="150" height="150" viewBox="0 0 180 180">
              <g transform="rotate(-90 90 90)">
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.critical} strokeWidth="18"
                  strokeDasharray={`${(criticalPct / 100) * circumference} ${circumference}`} />
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.high} strokeWidth="18"
                  strokeDasharray={`${(highPct / 100) * circumference} ${circumference}`}
                  strokeDashoffset={`-${(criticalPct / 100) * circumference}`} />
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.medium} strokeWidth="18"
                  strokeDasharray={`${(mediumPct / 100) * circumference} ${circumference}`}
                  strokeDashoffset={`-${((criticalPct + highPct) / 100) * circumference}`} />
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.low} strokeWidth="18"
                  strokeDasharray={`${(lowPct / 100) * circumference} ${circumference}`}
                  strokeDashoffset={`-${((criticalPct + highPct + mediumPct) / 100) * circumference}`} />
              </g>
              <text x="90" y="95" textAnchor="middle" fontSize="18" fontWeight="bold">{total}</text>
              <text x="90" y="115" textAnchor="middle" fontSize="12">Accidents</text>
            </svg>
            <div>
              <p><span style={{ color: severityColors.critical }}>⬤</span> Critical: {monthlyData.critical}</p>
              <p><span style={{ color: severityColors.high }}>⬤</span> High: {monthlyData.high}</p>
              <p><span style={{ color: severityColors.medium }}>⬤</span> Medium: {monthlyData.medium}</p>
              <p><span style={{ color: severityColors.low }}>⬤</span> Low: {monthlyData.low}</p>
            </div>
          </div>
          <h4 style={{ marginTop: "15px", textAlign: "center" }}>
            🚦 Safety Status:{" "}
            <span style={{
              color:
                safetyStatus === "Critical" ? "#d32f2f" :
                safetyStatus === "Poor" ? "red" :
                safetyStatus === "Average" ? "orange" :
                "green"
            }}>{safetyStatus}</span>
          </h4>
        </div>

        {/* Connected Devices */}
        <div style={{
          flex: "1",
          minWidth: "300px",
          backgroundColor: "#fff",
          borderRadius: "10px",
          padding: "20px",
          boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
        }}>
          <h3 style={{ textAlign: "center" }}>📡 Connected Devices ({devices.length})</h3>
          <div style={{ maxHeight: "250px", overflowY: "auto" }}>
            {devices.map((device, index) => (
              <div key={index} style={{
                padding: "10px",
                margin: "5px 0",
                backgroundColor: "#f5f5f5",
                borderRadius: "5px",
                borderLeft: `4px solid ${device.status === 'online' ? 'green' : 'gray'}`
              }}>
                <div><strong>{device.device_id}</strong></div>
                <div style={{ fontSize: "0.9em", color: "#666" }}>
                  📍 {device.location}
                  <br />
                  📏 {device.distance}cm | 💥 {device.total_impacts} impacts
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Accident Records Table */}
      <div style={{ marginBottom: "40px" }}>
        <h3>🚗 Accident Records (Last 24h)</h3>
        {accidentHistory.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{
              width: "100%",
              borderCollapse: "collapse",
              textAlign: "left",
              backgroundColor: "#fff",
              boxShadow: "0 4px 8px rgba(0,0,0,0.2)"
            }}>
              <thead style={{ backgroundColor: "#f2f2f2" }}>
                <tr>
                  <th style={{ padding: "12px", border: "1px solid #ddd" }}>Time</th>
                  <th style={{ padding: "12px", border: "1px solid #ddd" }}>Location</th>
                  <th style={{ padding: "12px", border: "1px solid #ddd" }}>Distance (cm)</th>
                  <th style={{ padding: "12px", border: "1px solid #ddd" }}>Impacts</th>
                  <th style={{ padding: "12px", border: "1px solid #ddd" }}>Severity</th>
                </tr>
              </thead>
              <tbody>
                {accidentHistory.map((acc, index) => (
                  <tr key={index} style={{ borderBottom: "1px solid #ddd" }}>
                    <td style={{ padding: "12px" }}>{acc.time}</td>
                    <td style={{ padding: "12px" }}>{acc.location}</td>
                    <td style={{ padding: "12px" }}>{acc.distance}</td>
                    <td style={{ padding: "12px" }}>{acc.totalImpacts}</td>
                    <td style={{
                      padding: "12px",
                      color: severityColors[acc.severity],
                      fontWeight: "bold"
                    }}>{acc.severity.toUpperCase()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <p>No accident records in the last 24 hours</p>}
      </div>

      {/* Active Alerts */}
      {alerts.length > 0 && (
        <div style={{ marginBottom: "40px" }}>
          <h3>🔔 Active Alerts ({alerts.filter(a => !a.read).length} unread)</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {alerts.filter(a => !a.read).slice(0, 5).map((alert, index) => (
              <div key={index} style={{
                backgroundColor: "#fff",
                padding: "15px",
                borderRadius: "8px",
                borderLeft: `5px solid ${severityColors[alert.severity]}`,
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)"
              }}>
                <strong>{alert.title}</strong>
                <br />
                <span style={{ fontSize: "0.9em", color: "#666" }}>{alert.message}</span>
                <br />
                <span style={{ fontSize: "0.8em", color: "#999" }}>
                  {new Date(alert.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

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

export default AccidentDetection;