import React, { useEffect, useState } from "react";

function AccidentDetection() {
  const [accidentAlert, setAccidentAlert] = useState({
    detected: false,
    location: "",
    severity: "",
    time: ""
  });

  const [accidentHistory, setAccidentHistory] = useState([]);
  const [emergencyResponse, setEmergencyResponse] = useState({
    notified: false,
    notifiedTime: "",
    responders: [
      { type: "Ambulance", status: "Available", eta: "" },
      { type: "Police", status: "Available", eta: "" }
    ]
  });

  const [monthlyData] = useState({
    month: "January 2026",
    low: 8,
    medium: 12,
    high: 8
  });

  const radius = 70;
  const circumference = 2 * Math.PI * radius;

  const severityColors = {
    High: "#f44336",
    Medium: "#4caf50",
    Low: "#ffeb3b"
  };

  const severityToNumber = (severity) => {
    switch (severity) {
      case "Low": return 1;
      case "Medium": return 2;
      case "High": return 3;
      default: return 0;
    }
  };

  const getAlertStyle = () => ({
    backgroundColor: severityColors[accidentAlert.severity] || "#ddd",
    color: accidentAlert.severity === "Low" ? "#000" : "#fff"
  });

  const blinkStyle = accidentAlert.severity === "High"
    ? { animation: "blink 1s infinite" }
    : {};

  const getResponderColor = (status) => {
    switch (status) {
      case "Available": return "green";
      case "Busy": return "orange";
      case "Offline": return "red";
      default: return "black";
    }
  };

  const activeCount = emergencyResponse.responders.filter(r => r.status !== "Available").length;
  const availableCount = emergencyResponse.responders.filter(r => r.status === "Available").length;

  const total = monthlyData.low + monthlyData.medium + monthlyData.high;
  const lowPct = (monthlyData.low / total) * 100;
  const mediumPct = (monthlyData.medium / total) * 100;
  const highPct = (monthlyData.high / total) * 100;

  const safetyStatus =
    monthlyData.high > 10 ? "Poor" :
    monthlyData.medium > 10 ? "Average" :
    "Good";

  // =================== LOAD PERSISTENT STATE ===================
  useEffect(() => {
    const savedAlert = localStorage.getItem("accidentAlert");
    const savedHistory = localStorage.getItem("accidentHistory");
    const savedEmergency = localStorage.getItem("emergencyResponse");

    if (savedAlert) setAccidentAlert(JSON.parse(savedAlert));
    if (savedHistory) setAccidentHistory(JSON.parse(savedHistory));
    if (savedEmergency) setEmergencyResponse(JSON.parse(savedEmergency));
  }, []);

  // =================== ACCIDENT SIMULATION ===================
  useEffect(() => {
    const accidentInterval = setInterval(() => {
      const severities = ["Low", "Medium", "High"];
      const severity = severities[Math.floor(Math.random() * severities.length)];

      const locations = [
        "Main Road Junction A",
        "Highway Section B",
        "Downtown Intersection",
        "Bridge Approach",
        "Tunnel Entrance",
        "School Zone"
      ];
      const location = locations[Math.floor(Math.random() * locations.length)];

      const now = new Date();
      const time = now.toLocaleTimeString();

      // Update top alert
      const newAlert = { detected: true, location, severity, time };
      setAccidentAlert(newAlert);
      localStorage.setItem("accidentAlert", JSON.stringify(newAlert));

      // Add new accident and remove older than 1 hour
      setAccidentHistory(prev => {
        const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
        const updated = prev.filter(acc => new Date(acc.date) > oneHourAgo);
        const newHistory = [...updated, { severity, time, location, date: now }];
        localStorage.setItem("accidentHistory", JSON.stringify(newHistory));
        return newHistory;
      });

      // Notify emergency responders
      setEmergencyResponse(prev => {
        const updated = {
          ...prev,
          notified: true,
          notifiedTime: time,
          responders: prev.responders.map(res => ({
            ...res,
            status: "available",
            eta: `${Math.floor(Math.random() * 10 + 5)} mins`
          }))
        };
        localStorage.setItem("emergencyResponse", JSON.stringify(updated));
        return updated;
      });
    }, 30000);

    return () => clearInterval(accidentInterval);
  }, []);

  // =================== AUTO-UPDATE RESPONDERS ===================
  useEffect(() => {
    const interval = setInterval(() => {
      setEmergencyResponse(prev => {
        const updatedResponders = prev.responders.map(res => {
          if (res.status === "Busy") return { ...res, status: "Available", eta: "" };
          return res;
        });
        const updated = { ...prev, responders: updatedResponders };
        localStorage.setItem("emergencyResponse", JSON.stringify(updated));
        return updated;
      });
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  // =================== SOUND ALERTS ===================
  useEffect(() => {
    if (!accidentAlert.detected) return;

    let soundUrl = "";
    switch (accidentAlert.severity) {
      case "High":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"; // loud
        break;
      case "Medium":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"; // medium
        break;
      case "Low":
        soundUrl = "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg"; // soft
        break;
      default:
        return;
    }

    const audio = new Audio(soundUrl);
    audio.play();
  }, [accidentAlert]);

  // =================== RENDER ===================
  return (
    <div style={{ padding: "20px", fontFamily: "Arial, sans-serif" }}>
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
          🚨 ACCIDENT ALERT ({accidentAlert.severity})
          <br />
          📍 Location: {accidentAlert.location}
          <br />
          ⏰ Time: {accidentAlert.time}
        </div>
      )}

      <h2 style={{ marginBottom: "20px" }}>🚑 Accident Detection & Emergency Response</h2>

      {/* Dashboard */}
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", marginBottom: "40px" }}>
        {/* Monthly Accident Rating */}
        <div style={{
          width: "400px",
          backgroundColor: "#fff",
          borderRadius: "10px",
          padding: "20px",
          boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
        }}>
          <h3 style={{ textAlign: "center" }}>📊 Monthly Accident Rating – {monthlyData.month}</h3>
          <div style={{ display: "flex", gap: "20px", alignItems: "center", justifyContent: "center" }}>
            <svg width="150" height="150" viewBox="0 0 180 180">
              <g transform="rotate(-90 90 90)">
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.High} strokeWidth="18"
                  strokeDasharray={`${(highPct / 100) * circumference} ${circumference}`} />
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.Medium} strokeWidth="18"
                  strokeDasharray={`${(mediumPct / 100) * circumference} ${circumference}`}
                  strokeDashoffset={`-${(highPct / 100) * circumference}`} />
                <circle cx="90" cy="90" r={radius} fill="none" stroke={severityColors.Low} strokeWidth="18"
                  strokeDasharray={`${(lowPct / 100) * circumference} ${circumference}`}
                  strokeDashoffset={`-${((highPct + mediumPct) / 100) * circumference}`} />
              </g>
              <text x="90" y="95" textAnchor="middle" fontSize="18" fontWeight="bold">{total}</text>
              <text x="90" y="115" textAnchor="middle" fontSize="12">Accidents</text>
            </svg>
            <div>
              <p><span style={{ color: severityColors.High }}>⬤</span> High: {monthlyData.high}</p>
              <p><span style={{ color: severityColors.Medium }}>⬤</span> Medium: {monthlyData.medium}</p>
              <p><span style={{ color: severityColors.Low }}>⬤</span> Low: {monthlyData.low}</p>
            </div>
          </div>
          <h4 style={{ marginTop: "15px", textAlign: "center" }}>
            🚦 Overall Safety Status:{" "}
            <span style={{
              color:
                safetyStatus === "Poor" ? "red" :
                safetyStatus === "Average" ? "orange" :
                "green"
            }}>{safetyStatus}</span>
          </h4>
        </div>

        {/* Accident Severity History */}
        {accidentHistory.length > 0 && (
          <div style={{
            width: "400px",
            backgroundColor: "#fff",
            borderRadius: "10px",
            padding: "20px",
            boxShadow: "0 8px 16px rgba(0,0,0,0.25)"
          }}>
            <h3 style={{ textAlign: "center" }}>📈 Accident Severity Over Time</h3>
            <svg width="360" height="180">
              <line x1="40" y1="160" x2="340" y2="160" stroke="#000" strokeWidth="2"/>
              <line x1="40" y1="20" x2="40" y2="160" stroke="#000" strokeWidth="2"/>
              {accidentHistory.map((acc, index) => {
                if(index === 0) return null;
                const prev = accidentHistory[index-1];
                const x1 = 40 + (index-1) * 30;
                const y1 = 160 - severityToNumber(prev.severity) * 40;
                const x2 = 40 + index * 30;
                const y2 = 160 - severityToNumber(acc.severity) * 40;
                return <line key={index} x1={x1} y1={y1} x2={x2} y2={y2} stroke={severityColors[acc.severity]} strokeWidth="2"/>
              })}
              {accidentHistory.map((acc, index) => {
                const cx = 40 + index * 30;
                const cy = 160 - severityToNumber(acc.severity) * 40;
                return <circle key={index} cx={cx} cy={cy} r="5" fill={severityColors[acc.severity]}/>
              })}
              <text x="0" y="40" fontSize="12">High</text>
              <text x="0" y="80" fontSize="12">Medium</text>
              <text x="0" y="120" fontSize="12">Low</text>
            </svg>
          </div>
        )}
      </div>

      {/* Accident Records Table */}
      <div style={{ marginBottom: "40px" }}>
        <h3> Accident Records (last 1 hour)</h3>
        {accidentHistory.length > 0 ? (
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            textAlign: "left",
            boxShadow: "0 4px 8px rgba(0,0,0,0.2)"
          }}>
            <thead style={{ backgroundColor: "#f2f2f2" }}>
              <tr>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>Time</th>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>Location</th>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {accidentHistory.map((acc, index) => (
                <tr key={index} style={{ borderBottom: "1px solid #ddd" }}>
                  <td style={{ padding: "12px" }}>{acc.time}</td>
                  <td style={{ padding: "12px" }}>{acc.location}</td>
                  <td style={{ padding: "12px", color: severityColors[acc.severity] }}>{acc.severity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p>No accident records in the last 1 hour.</p>}
      </div>

      {/* Emergency Response */}
      {emergencyResponse.notified && (
        <div style={{ marginBottom: "40px" }}>
          <h3>🚑 Emergency Responders Notification</h3>
          <p>📨 Notified at: <strong>{emergencyResponse.notifiedTime}</strong></p>
          <p>🟢 Available: {availableCount} | 🔴 Busy: {activeCount}</p>
          <table style={{
            width: "100%",
            borderCollapse: "collapse",
            textAlign: "left",
            boxShadow: "0 4px 8px rgba(0,0,0,0.2)"
          }}>
            <thead style={{ backgroundColor: "#f2f2f2" }}>
              <tr>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>Responder</th>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>Status</th>
                <th style={{ padding: "12px", border: "1px solid #ddd" }}>ETA</th>
              </tr>
            </thead>
            <tbody>
              {emergencyResponse.responders.map((res, index) => (
                <tr key={index} style={{ borderBottom: "1px solid #ddd" }}>
                  <td style={{ padding: "12px" }}>{res.type}</td>
                  <td style={{ padding: "12px", color: getResponderColor(res.status) }}>{res.status}</td>
                  <td style={{ padding: "12px" }}>{res.eta}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
