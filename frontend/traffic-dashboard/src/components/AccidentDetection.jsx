import React, { useEffect, useState, useRef } from "react";

const API_URL = "http://localhost:8000/api";

// ─── small helpers ────────────────────────────────────────────────────────────
const isYes = (v) => String(v).trim().toUpperCase() === "YES";

const thStyle = {
  padding: "12px 14px",
  border: "1px solid #ddd",
  backgroundColor: "#f2f2f2",
  fontWeight: "600",
  textAlign: "left",
  whiteSpace: "nowrap",
};

const tdStyle = {
  padding: "11px 14px",
  border: "1px solid #ddd",
  fontSize: "0.92em",
};

// ─── component ────────────────────────────────────────────────────────────────
export default function AccidentDetection() {
  // Latest accident for the banner
  const [latestAlert, setLatestAlert] = useState(null);

  // Full history shown in the table
  const [history, setHistory] = useState([]);

  // Stats card
  const [stats, setStats] = useState({
    total: 0,
    last24h: 0,
    activeAlerts: 0,
    connectedDevices: 0,
    mlActive: false,
    vibrationYes: 0,
    vibrationNo: 0,
    latestDistance: 0,
  });

  // Unread alerts panel
  const [alerts, setAlerts] = useState([]);

  // Connected devices
  const [devices, setDevices] = useState([]);

  // Loading / error state
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState("");

  // Prevent audio spam — only play when latest record actually changes
  const prevAlertRef = useRef(null);

  // ── fetch accidents ──────────────────────────────────────────────────────
  const fetchAccidents = async () => {
    try {
      const res  = await fetch(`${API_URL}/accidents`);
      const data = await res.json();

      if (!data.success) {
        console.warn("API returned success=false:", data);
        setFetchError(`Backend error: ${data.error || "unknown"}`);
        return;
      }

      const accidents = data.accidents || [];

      // Build formatted history (newest first for the table)
      const formatted = accidents.map((acc) => ({
        date:      acc.date      || "",
        latitude:  acc.latitude  || "",
        longitude: acc.longitude || "",
        vibration: acc.vibration || "",
        distance:  acc.distance  ?? 0,
      }));

      setHistory([...formatted].reverse());   // newest first in table
      setFetchError("");

      // Compute vibration counts
      const yesCount = formatted.filter((x) => isYes(x.vibration)).length;
      const noCount  = formatted.length - yesCount;
      const last     = formatted[formatted.length - 1] ?? null;

      setStats((prev) => ({
        ...prev,
        total:           formatted.length,
        vibrationYes:    yesCount,
        vibrationNo:     noCount,
        latestDistance:  last ? last.distance : 0,
      }));

      // Update banner only when the latest record changes
      if (last) {
        const key = `${last.date}|${last.vibration}|${last.distance}`;
        if (prevAlertRef.current !== key) {
          prevAlertRef.current = key;
          setLatestAlert(last);
        }
      }
    } catch (err) {
      console.error("fetchAccidents error:", err);
      setFetchError("Cannot reach backend — is the Flask server running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  // ── fetch /api/statistics ────────────────────────────────────────────────
  const fetchStatistics = async () => {
    try {
      const res  = await fetch(`${API_URL}/statistics`);
      const data = await res.json();
      if (data.success) {
        setStats((prev) => ({
          ...prev,
          last24h:          data.statistics.accidents_last_24h    ?? prev.last24h,
          activeAlerts:     data.statistics.active_alerts         ?? prev.activeAlerts,
          connectedDevices: data.statistics.connected_devices     ?? prev.connectedDevices,
          mlActive:         data.statistics.ml_models_active      ?? prev.mlActive,
        }));
      }
    } catch (err) {
      console.warn("fetchStatistics error:", err);
    }
  };

  // ── fetch alerts ─────────────────────────────────────────────────────────
  const fetchAlerts = async () => {
    try {
      const res  = await fetch(`${API_URL}/alerts`);
      const data = await res.json();
      if (data.success) {
        setAlerts((data.alerts || []).map((a) => ({ ...a, read: a.read ?? false })));
      }
    } catch (err) {
      console.warn("fetchAlerts error:", err);
    }
  };

  // ── fetch devices ────────────────────────────────────────────────────────
  const fetchDevices = async () => {
    try {
      const res  = await fetch(`${API_URL}/devices`);
      const data = await res.json();
      if (data.success) setDevices(data.devices || []);
    } catch (err) {
      console.warn("fetchDevices error:", err);
    }
  };

  // ── poll everything ──────────────────────────────────────────────────────
  useEffect(() => {
    fetchAccidents();
    fetchStatistics();
    fetchAlerts();
    fetchDevices();

    const id = setInterval(() => {
      fetchAccidents();
      fetchStatistics();
      fetchAlerts();
      fetchDevices();
    }, 5000);

    return () => clearInterval(id);
  }, []);

  // ── audio alert when latest record changes ───────────────────────────────
  useEffect(() => {
    if (!latestAlert) return;
    const url = isYes(latestAlert.vibration)
      ? "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"
      : "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg";
    const audio = new Audio(url);
    audio.play().catch(() => {});   // browsers may block autoplay — that's fine
  }, [latestAlert]);

  // ─── derived colours ──────────────────────────────────────────────────────
  const bannerBg  = latestAlert && isYes(latestAlert.vibration) ? "#e53935" : "#43a047";
  const unreadCount = alerts.filter((a) => !a.read).length;

  // ─── render ───────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: "20px", fontFamily: "'Segoe UI', Arial, sans-serif", backgroundColor: "#f0f2f5", minHeight: "100vh" }}>

      {/* ── Error banner ──────────────────────────────────────────────────── */}
      {fetchError && (
        <div style={{
          backgroundColor: "#fff3cd", color: "#856404", border: "1px solid #ffc107",
          padding: "12px 16px", borderRadius: "6px", marginBottom: "16px", fontWeight: 500,
        }}>
          ⚠️ {fetchError}
        </div>
      )}

      {/* ── Latest-accident banner ────────────────────────────────────────── */}
      {latestAlert && (
        <div style={{
          backgroundColor: bannerBg,
          color: "#fff",
          padding: "14px 18px",
          borderRadius: "8px",
          marginBottom: "20px",
          fontWeight: "bold",
          boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
          lineHeight: "1.7",
          animation: isYes(latestAlert.vibration) ? "blink 1s infinite" : "none",
        }}>
          🚨 LATEST ACCIDENT RECORD
          <br />📅 Date: {latestAlert.date || "—"}
          <br />📍 Lat: {latestAlert.latitude || "—"} &nbsp;|&nbsp; Lng: {latestAlert.longitude || "—"}
          <br />💥 Vibration: <strong>{latestAlert.vibration}</strong>
          &nbsp;|&nbsp;
          📏 Distance: <strong>{latestAlert.distance} cm</strong>
          &nbsp;|&nbsp;
          Status: <strong>{isYes(latestAlert.vibration) ? "⚠️ Impact Detected" : "✅ Normal"}</strong>
        </div>
      )}

      <h2 style={{ marginBottom: "20px", color: "#1a237e" }}>
        🚑 ML-Powered Accident Detection System
      </h2>

      {/* ── System status card ───────────────────────────────────────────── */}
      <div style={cardStyle}>
        <h3 style={sectionTitle}>📊 System Status</h3>
        {loading ? (
          <p style={{ color: "#888" }}>Loading data from Google Sheets…</p>
        ) : (
          <div style={{ display: "flex", gap: "28px", flexWrap: "wrap" }}>
            <StatItem label="Total Records"      value={stats.total} />
            <StatItem label="Last 24 h"          value={stats.last24h} />
            <StatItem label="Active Alerts"      value={stats.activeAlerts} />
            <StatItem label="Connected Devices"  value={stats.connectedDevices} />
            <StatItem label="Vibration YES"      value={stats.vibrationYes}    valueColor="#e53935" />
            <StatItem label="Vibration NO"       value={stats.vibrationNo}     valueColor="#43a047" />
            <StatItem label="Latest Distance"    value={`${stats.latestDistance} cm`} />
            <StatItem
              label="ML Models"
              value={stats.mlActive ? "✓ Active" : "✗ Inactive"}
              valueColor={stats.mlActive ? "#43a047" : "#e53935"}
            />
          </div>
        )}
      </div>

      {/* ── Info cards row ───────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: "20px", flexWrap: "wrap", marginBottom: "28px" }}>

        {/* Latest Location */}
        <div style={{ ...cardStyle, flex: "1", minWidth: "260px" }}>
          <h3 style={sectionTitle}>📍 Latest Location</h3>
          <p><strong>Latitude:</strong>  {latestAlert?.latitude  || "No data"}</p>
          <p><strong>Longitude:</strong> {latestAlert?.longitude || "No data"}</p>
          <p><strong>Date:</strong>      {latestAlert?.date      || "No data"}</p>
          {latestAlert?.latitude && latestAlert?.longitude && (
            <a
              href={`https://maps.google.com/?q=${latestAlert.latitude},${latestAlert.longitude}`}
              target="_blank"
              rel="noreferrer"
              style={{ color: "#1565c0", fontSize: "0.9em" }}
            >
              🗺️ Open in Google Maps
            </a>
          )}
        </div>

        {/* Sensor data */}
        <div style={{ ...cardStyle, flex: "1", minWidth: "260px" }}>
          <h3 style={sectionTitle}>🔧 Sensor Data</h3>
          <p>
            <strong>Vibration:</strong>{" "}
            <span style={{ color: isYes(latestAlert?.vibration) ? "#e53935" : "#43a047", fontWeight: "bold" }}>
              {latestAlert?.vibration || "No data"}
            </span>
          </p>
          <p><strong>Distance:</strong> {latestAlert ? `${latestAlert.distance} cm` : "No data"}</p>
          <p>
            <strong>Status:</strong>{" "}
            <span style={{ color: isYes(latestAlert?.vibration) ? "#e53935" : "#43a047", fontWeight: "bold" }}>
              {latestAlert
                ? (isYes(latestAlert.vibration) ? "⚠️ Impact Detected" : "✅ Normal")
                : "No data"}
            </span>
          </p>
        </div>

        {/* Connected devices */}
        <div style={{ ...cardStyle, flex: "1", minWidth: "260px" }}>
          <h3 style={sectionTitle}>📡 Connected Devices ({devices.length})</h3>
          <div style={{ maxHeight: "180px", overflowY: "auto" }}>
            {devices.length === 0 ? (
              <p style={{ color: "#999" }}>No devices connected</p>
            ) : (
              devices.map((d, i) => (
                <div key={i} style={{
                  padding: "8px 10px", margin: "4px 0",
                  backgroundColor: "#f5f5f5", borderRadius: "5px",
                  borderLeft: `4px solid ${d.status === "online" ? "#43a047" : "#9e9e9e"}`,
                }}>
                  <strong>{d.device_id}</strong>
                  <div style={{ fontSize: "0.85em", color: "#555", marginTop: "2px" }}>
                    📍 {d.location}<br />
                    📏 {d.distance} cm &nbsp;|&nbsp; 💥 {d.vibration}<br />
                    🕐 {d.last_seen}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* ── Accident records table ───────────────────────────────────────── */}
      <div style={cardStyle}>
        <h3 style={sectionTitle}>🚗 Accident Records ({history.length})</h3>

        {loading && <p style={{ color: "#888" }}>Fetching records from Google Sheets…</p>}

        {!loading && history.length === 0 && !fetchError && (
          <p style={{ color: "#777" }}>No accident records found in Google Sheets.</p>
        )}

        {history.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table style={{
              width: "100%", borderCollapse: "collapse",
              backgroundColor: "#fff", fontSize: "0.93em",
            }}>
              <thead>
                <tr>
                  <th style={thStyle}>#</th>
                  <th style={thStyle}>Date</th>
                  <th style={thStyle}>Latitude</th>
                  <th style={thStyle}>Longitude</th>
                  <th style={thStyle}>Vibration</th>
                  <th style={thStyle}>Distance (cm)</th>
                  <th style={thStyle}>Maps</th>
                </tr>
              </thead>
              <tbody>
                {history.map((acc, i) => (
                  <tr
                    key={i}
                    style={{ backgroundColor: isYes(acc.vibration) ? "#fce4ec" : "#f9f9f9" }}
                  >
                    <td style={tdStyle}>{i + 1}</td>
                    <td style={tdStyle}>{acc.date      || "—"}</td>
                    <td style={tdStyle}>{acc.latitude  || "—"}</td>
                    <td style={tdStyle}>{acc.longitude || "—"}</td>
                    <td style={{ ...tdStyle, fontWeight: "bold", color: isYes(acc.vibration) ? "#c62828" : "#2e7d32" }}>
                      {acc.vibration || "—"}
                    </td>
                    <td style={tdStyle}>{acc.distance}</td>
                    <td style={tdStyle}>
                      {acc.latitude && acc.longitude ? (
                        <a
                          href={`https://maps.google.com/?q=${acc.latitude},${acc.longitude}`}
                          target="_blank"
                          rel="noreferrer"
                          style={{ color: "#1565c0", textDecoration: "none" }}
                        >
                          🗺️
                        </a>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Active alerts panel ───────────────────────────────────────────── */}
      {alerts.length > 0 && (
        <div style={{ ...cardStyle, marginTop: "24px" }}>
          <h3 style={sectionTitle}>🔔 Active Alerts ({unreadCount} unread)</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {alerts.filter((a) => !a.read).slice(0, 5).map((alert, i) => {
              const borderColor =
                alert.severity === "critical" ? "#b71c1c" :
                alert.severity === "high"     ? "#e53935" :
                alert.severity === "medium"   ? "#f57c00" : "#43a047";
              return (
                <div key={i} style={{
                  backgroundColor: "#fff", padding: "14px", borderRadius: "8px",
                  borderLeft: `5px solid ${borderColor}`,
                  boxShadow: "0 1px 4px rgba(0,0,0,0.12)",
                }}>
                  <strong>{alert.title}</strong>
                  <br />
                  <span style={{ fontSize: "0.9em", color: "#555" }}>{alert.message}</span>
                  <br />
                  <span style={{ fontSize: "0.8em", color: "#999" }}>
                    {new Date(alert.timestamp).toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style>{`
        @keyframes blink {
          0%   { opacity: 1; }
          50%  { opacity: 0.45; }
          100% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ─── tiny sub-components ──────────────────────────────────────────────────────
function StatItem({ label, value, valueColor }) {
  return (
    <div style={{ minWidth: "100px" }}>
      <div style={{ fontSize: "0.78em", color: "#777", marginBottom: "2px" }}>{label}</div>
      <div style={{ fontWeight: "700", fontSize: "1.05em", color: valueColor || "#222" }}>{value}</div>
    </div>
  );
}

// ─── shared styles ────────────────────────────────────────────────────────────
const cardStyle = {
  backgroundColor: "#fff",
  padding: "18px 20px",
  borderRadius: "10px",
  marginBottom: "22px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.10)",
};

const sectionTitle = {
  margin: "0 0 14px 0",
  fontSize: "1em",
  color: "#37474f",
  borderBottom: "1px solid #eceff1",
  paddingBottom: "8px",
};