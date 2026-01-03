import React, { useEffect, useState } from "react";

function AccidentDetection() {

  /* ================= ACCIDENT ALERT (HARDCODED) ================= */
  const [accidentAlert, setAccidentAlert] = useState({
    detected: true,
    location: "Highway Section B",
    severity: "High", // High | Medium | Low
    time: "2026-01-03 14:25"
  });

  /* ================= EMERGENCY RESPONDERS (SIMULATION) ================= */
  const [emergencyResponse, setEmergencyResponse] = useState({
    notified: accidentAlert.detected,
    notifiedTime: "2026-01-03 14:26",
    responders: [
      { type: "Ambulance", status: "Busy", eta: "8 mins" },
      { type: "Police", status: "Available", eta: "5 mins" }
      // Fire Brigade removed
    ]
  });

  /* ================= ALERT COLOR LOGIC ================= */
  const getAlertStyle = () => {
    switch (accidentAlert.severity) {
      case "High":
        return { backgroundColor: "#f44336", color: "white" };
      case "Medium":
        return { backgroundColor: "#ffeb3b", color: "black" };
      case "Low":
        return { backgroundColor: "#4caf50", color: "white" };
      default:
        return {};
    }
  };

  /* ================= SOUND ALERT FOR HIGH ================= */
  useEffect(() => {
    if (accidentAlert.detected && accidentAlert.severity === "High") {
      const audio = new Audio(
        "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"
      );
      audio.play();
    }
  }, []);

  /* ================= MONTHLY DATA ================= */
  const data = {
    month: "January 2026",
    low: 8,
    medium: 12,
    high: 8
  };

  const total = data.low + data.medium + data.high;
  const lowPct = (data.low / total) * 100;
  const mediumPct = (data.medium / total) * 100;
  const highPct = (data.high / total) * 100;

  const radius = 70;
  const circumference = 2 * Math.PI * radius;

  /* ================= SAFETY STATUS ================= */
  const safetyStatus =
    data.high > 10 ? "Poor" :
    data.medium > 10 ? "Average" :
    "Good";

  /* ================= BLINK EFFECT ================= */
  const blinkStyle =
    accidentAlert.severity === "High"
      ? { animation: "blink 1s infinite" }
      : {};

  /* ================= AUTO-UPDATE RESPONDER STATUS ================= */
  useEffect(() => {
    const interval = setInterval(() => {
      setEmergencyResponse(prev => {
        const updatedResponders = prev.responders.map(res => {
          if (res.status === "Busy") {
            // simulate task finished randomly
            return { ...res, status: "Available" };
          }
          return res;
        });
        return { ...prev, responders: updatedResponders };
      });
    }, 60000); // every 60 seconds
    return () => clearInterval(interval);
  }, []);

  /* ================= COUNT ACTIVE/AVAILABLE RESPONDERS ================= */
  const activeCount = emergencyResponse.responders.filter(r => r.status !== "Available").length;
  const availableCount = emergencyResponse.responders.filter(r => r.status === "Available").length;

  /* ================= GET RESPONDER COLOR ================= */
  const getResponderColor = (status) => {
    switch(status){
      case "Available": return "green";
      case "Busy": return "orange";
      case "Offline": return "red";
      default: return "black";
    }
  }

  return (
    <div style={{ padding: "20px" }}>

      {/* ================= TOP ALERT ================= */}
      {accidentAlert.detected && (
        <div
          style={{
            ...getAlertStyle(),
            ...blinkStyle,
            padding: "15px",
            borderRadius: "6px",
            marginBottom: "20px",
            fontWeight: "bold"
          }}
        >
          🚨 ACCIDENT ALERT ({accidentAlert.severity})
          <br />
          📍 Location: {accidentAlert.location}
          <br />
          ⏰ Time: {accidentAlert.time}
        </div>
      )}

      <h2>🚑 Accident Detection & Emergency Response</h2>
      <h3>📊 Monthly Accident Rating – {data.month}</h3>

      {/* ================= CIRCLE CHART ================= */}
      <div style={{ display: "flex", gap: "40px", alignItems: "center" }}>
        <svg width="180" height="180" viewBox="0 0 180 180">
          <g transform="rotate(-90 90 90)">
            <circle cx="90" cy="90" r={radius} fill="none" stroke="red" strokeWidth="18"
              strokeDasharray={`${(highPct / 100) * circumference} ${circumference}`} />
            <circle cx="90" cy="90" r={radius} fill="none" stroke="blue" strokeWidth="18"
              strokeDasharray={`${(mediumPct / 100) * circumference} ${circumference}`}
              strokeDashoffset={`-${(highPct / 100) * circumference}`} />
            <circle cx="90" cy="90" r={radius} fill="none" stroke="green" strokeWidth="18"
              strokeDasharray={`${(lowPct / 100) * circumference} ${circumference}`}
              strokeDashoffset={`-${((highPct + mediumPct) / 100) * circumference}`} />
          </g>

          <text x="90" y="95" textAnchor="middle" fontSize="20" fontWeight="bold">
            {total}
          </text>
          <text x="90" y="115" textAnchor="middle" fontSize="12">
            Accidents
          </text>
        </svg>

        <div>
          <p><span style={{ color: "red" }}>⬤</span> High: {data.high}</p>
          <p><span style={{ color: "blue" }}>⬤</span> Medium: {data.medium}</p>
          <p><span style={{ color: "green" }}>⬤</span> Low: {data.low}</p>
        </div>
      </div>

      {/* ================= SAFETY STATUS ================= */}
      <h3>
        🚦 Overall Safety Status:{" "}
        <span style={{
          color:
            safetyStatus === "Poor" ? "red" :
            safetyStatus === "Average" ? "orange" :
            "green"
        }}>
          {safetyStatus}
        </span>
      </h3>

      {/* ================= ACCIDENT RECORD ================= */}
      <h3>🗂️ Accident Record</h3>
      <table border="1" cellPadding="8" width="100%">
        <thead>
          <tr>
            <th>Time</th>
            <th>Location</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>{accidentAlert.time}</td>
            <td>{accidentAlert.location}</td>
            <td>{accidentAlert.severity}</td>
          </tr>
        </tbody>
      </table>

      {/* ================= EMERGENCY RESPONSE PANEL ================= */}
      {emergencyResponse.notified && (
        <>
          <h3>🚑 Emergency Responders Notification</h3>
          <p>📨 Notified at: <strong>{emergencyResponse.notifiedTime}</strong></p>
          <p>🟢 Available: {availableCount} | 🔴 Busy: {activeCount}</p>
          <table border="1" cellPadding="8" width="100%">
            <thead>
              <tr>
                <th>Responder</th>
                <th>Status</th>
                <th>ETA</th>
              </tr>
            </thead>
            <tbody>
              {emergencyResponse.responders.map((res, index) => (
                <tr key={index}>
                  <td>{res.type}</td>
                  <td style={{color: getResponderColor(res.status)}}>{res.status}</td>
                  <td>{res.eta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* ================= BLINK STYLE ================= */}
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
