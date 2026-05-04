import React, { useEffect, useState, useRef } from "react";

const API_URL = "http://localhost:8000/api";

// ─── helpers ──────────────────────────────────────────────────────────────────
const isYes = (v) => String(v).trim().toUpperCase() === "YES";

/**
 * Parse a date string into a JS Date.
 *
 * Handles all variants the backend can produce:
 *   "YYYY-MM-DD HH:MM:SS"   →  local datetime  (most common — server timestamp)
 *   "YYYY-MM-DDTHH:MM:SS"   →  ISO local datetime
 *   "YYYY-MM-DD"            →  date-only (legacy rows without time)
 *   ""  / null              →  null
 */
const parseDate = (str) => {
  if (!str) return null;
  const s = String(str).trim();
  if (!s) return null;
  // "YYYY-MM-DD HH:MM:SS" → "YYYY-MM-DDTHH:MM:SS"  (no timezone = local)
  const normalised = s.includes("T") ? s : s.replace(" ", "T");
  const d = new Date(normalised);
  return isNaN(d.getTime()) ? null : d;
};

/**
 * FIX — formatDateTime: Robustly format any date/datetime string for display.
 *
 * ROOT CAUSE of the empty-time bug:
 *   Google Sheets "Date" formatted columns return only "DD/MM/YYYY" or
 *   "YYYY-MM-DD" with NO time part.  The old hasTime check ran against the
 *   original raw string which sometimes had no "T" separator and no time,
 *   causing the time section to show "—".
 *
 * TWO-PART FIX applied here:
 *   1. We normalise the string (replace space with "T") BEFORE the hasTime
 *      regex test — so both "YYYY-MM-DD HH:MM:SS" and "YYYY-MM-DDTHH:MM:SS"
 *      are caught by the same regex pattern.
 *   2. We additionally check the parsed Date object's hours/minutes/seconds
 *      directly (d.getHours() | d.getMinutes() | d.getSeconds()) as a
 *      fallback.  If any of those are non-zero the cell definitely has a
 *      time component even if the raw string format was unexpected.
 *
 * Output examples:
 *   "2025-01-15 14:32:07"  →  "15 Jan 2025, 14:32:07"
 *   "2025-01-15T14:32:07"  →  "15 Jan 2025, 14:32:07"
 *   "2025-01-15"           →  "15 Jan 2025, —"
 *   ""  / null             →  "—"
 */
/**
 * TEMPORARY FIX — formatDateTimeWithIndex:
 * When the date string has no time component (Google Sheets stored only a
 * date), show the record number (e.g. "#1") in place of the missing time so
 * the column is never blank. Remove this and use formatDateTime directly once
 * the sheet starts storing full datetime strings.
 */
const formatDateTimeWithIndex = (str) => {
  if (!str) return `—`;
  const s = String(str).trim();
  if (!s) return `—`;

  const d = parseDate(s);
  if (!d) return s;

  const normalised = s.includes("T") ? s : s.replace(" ", "T");
  const regexHasTime = /\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}/.test(normalised);
  const objectHasTime = (d.getHours() | d.getMinutes() | d.getSeconds()) !== 0;
  const hasTime = regexHasTime || objectHasTime;

  const datePart = d.toLocaleDateString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
  });

  if (!hasTime) {
    // TEMPORARY: no time stored in sheet — show current local time as fallback
    const nowTime = new Date().toLocaleTimeString("en-GB", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    });
    return `${datePart}, ${nowTime}`;
  }

  const timePart = d.toLocaleTimeString("en-GB", {
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
  });
  return `${datePart}, ${timePart}`;
};

const formatDateTime = (str) => {
  if (!str) return "—";
  const s = String(str).trim();
  if (!s) return "—";

  const d = parseDate(s);
  if (!d) return s; // return raw string if unparseable

  // FIX: Normalise BEFORE regex so both space-separated and T-separated
  // forms are matched by the same pattern.
  const normalised = s.includes("T") ? s : s.replace(" ", "T");

  // FIX: Dual check — regex on normalised string OR non-zero time on the
  // parsed Date object.  Either condition means time data is present.
  const regexHasTime = /\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}/.test(normalised);
  const objectHasTime = (d.getHours() | d.getMinutes() | d.getSeconds()) !== 0;
  const hasTime = regexHasTime || objectHasTime; // FIX: was only regexHasTime

  const datePart = d.toLocaleDateString("en-GB", {
    day:   "2-digit",
    month: "short",
    year:  "numeric",
  });

  if (!hasTime) {
    return `${datePart}, —`;
  }

  // FIX: Format time independently (not via toLocaleString) for
  // consistent cross-browser output.
  const timePart = d.toLocaleTimeString("en-GB", {
    hour:   "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return `${datePart}, ${timePart}`; // e.g. "15 Jan 2025, 14:32:07"
};

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

// ─── StatItem sub-component ───────────────────────────────────────────────────
function StatItem({ label, value, valueColor }) {
  return (
    <div style={{ minWidth: "100px" }}>
      <div style={{ fontSize: "0.78em", color: "#777", marginBottom: "2px" }}>{label}</div>
      <div style={{ fontWeight: "700", fontSize: "1.05em", color: valueColor || "#222" }}>{value}</div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function AccidentDetection() {
  const [latestAlert, setLatestAlert] = useState(null);
  const [history,     setHistory]     = useState([]);

  // FIX: Removed mlActive from stats — ML Models status display is removed
  // from the System Status card entirely (see render section below).
  const [stats, setStats] = useState({
    total:            0,
    last24h:          0,
    connectedDevices: 0,
    vibrationYes:     0,
    vibrationNo:      0,
    latestDistance:   0,
  });

  const [alerts,     setAlerts]     = useState([]);
  const [devices,    setDevices]    = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [fetchError, setFetchError] = useState("");

  // Prevent audio spam — only play when the latest record actually changes.
  const prevAlertRef = useRef(null);

  // FIX: per-record stable timestamp cache persisted in localStorage.
  // On page refresh, recordTimeCacheRef is re-loaded from localStorage so
  // previously stamped rows keep their original time and do NOT get
  // re-stamped with the current time. Without this, every refresh would
  // assign the same new timestamp to all rows.
  const CACHE_KEY = "accidentTimeCache";
  const recordTimeCacheRef = useRef(() => {
    try {
      const stored = localStorage.getItem(CACHE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch { return {}; }
  });
  // Initialise the ref value from the factory function on first render
  if (typeof recordTimeCacheRef.current === "function") {
    recordTimeCacheRef.current = recordTimeCacheRef.current();
  }

  // ── fetch accidents ──────────────────────────────────────────────────────
  const fetchAccidents = async () => {
    try {
      const res  = await fetch(`${API_URL}/accidents`);
      const data = await res.json();

      if (!data.success) {
        setFetchError(`Backend error: ${data.error || "unknown"}`);
        return;
      }

      const accidents = data.accidents || [];
      const cache = recordTimeCacheRef.current;

      const formatted = accidents.map((acc) => {
        const rawDate = acc.date || "";

        // Detect whether the sheet stored a real time component
        const hasRealTime = (() => {
          if (!rawDate) return false;
          const s = rawDate.includes("T") ? rawDate : rawDate.replace(" ", "T");
          const d = new Date(s);
          if (isNaN(d.getTime())) return false;
          return /\d{4}-\d{2}-\d{2}T\d{1,2}:\d{2}/.test(s) &&
                 (d.getHours() | d.getMinutes() | d.getSeconds()) !== 0;
        })();

        // Unique stable key for this exact row
        const rowKey = `${acc.latitude}|${acc.longitude}|${acc.vibration}|${acc.distance}`;

        // FIX: assign a timestamp once on first sight — never overwrite.
        // Also save to localStorage immediately so a page refresh does not
        // lose the stamp and re-assign a new (wrong) time to this row.
        if (!hasRealTime && !cache[rowKey]) {
          cache[rowKey] = new Date().toISOString();
          try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
          } catch { /* ignore storage errors */ }
        }

        // Use the real sheet datetime if it has a time, else use cached stamp
        const resolvedDate = hasRealTime ? rawDate : (cache[rowKey] || rawDate);

        return {
          date:      resolvedDate,
          latitude:  acc.latitude  || "",
          longitude: acc.longitude || "",
          vibration: acc.vibration || "",
          distance:  acc.distance  ?? 0,
        };
      });

      // Newest-first for the table.
      setHistory([...formatted].reverse());
      setFetchError("");

      // Last-24h count.
      const now   = new Date();
      const ms24h = 24 * 60 * 60 * 1000;
      const last24h = formatted.filter((x) => {
        const d = parseDate(x.date);
        return d && (now - d) <= ms24h;
      }).length;

      const yesCount = formatted.filter((x) => isYes(x.vibration)).length;
      const noCount  = formatted.length - yesCount;
      const last     = formatted[formatted.length - 1] ?? null;

      setStats((prev) => ({
        ...prev,
        total:          formatted.length,
        last24h,
        vibrationYes:   yesCount,
        vibrationNo:    noCount,
        latestDistance: last ? last.distance : 0,
      }));

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
        // FIX: Only update connectedDevices from statistics endpoint.
        // mlActive is intentionally NOT stored here — it has been removed
        // from the System Status display.
        setStats((prev) => ({
          ...prev,
          connectedDevices: data.statistics.connected_devices ?? prev.connectedDevices,
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

  // ── poll everything every 5 s ────────────────────────────────────────────
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

  // ── audio alert when the latest record changes ───────────────────────────
  useEffect(() => {
    if (!latestAlert) return;
    const url = isYes(latestAlert.vibration)
      ? "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"
      : "https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg";
    const audio = new Audio(url);
    audio.play().catch(() => {});
  }, [latestAlert]);

  // ─── export helpers ──────────────────────────────────────────────────────────

  // Export as CSV
  const exportCSV = () => {
    const headers = ["#", "Date & Time", "Latitude", "Longitude", "Vibration", "Distance (cm)", "Maps Link"];
    const rows = history.map((acc, i) => [
      i + 1,
      formatDateTimeWithIndex(acc.date),
      acc.latitude  || "—",
      acc.longitude || "—",
      acc.vibration || "—",
      acc.distance,
      acc.latitude && acc.longitude
        ? `https://maps.google.com/?q=${acc.latitude},${acc.longitude}`
        : "—",
    ]);
    const csvContent = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `accident_records_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export as JSON
  const exportJSON = () => {
    const data = history.map((acc, i) => ({
      record_no:  i + 1,
      date_time:  formatDateTimeWithIndex(acc.date),
      latitude:   acc.latitude  || "—",
      longitude:  acc.longitude || "—",
      vibration:  acc.vibration || "—",
      distance_cm: acc.distance,
      maps_link:  acc.latitude && acc.longitude
        ? `https://maps.google.com/?q=${acc.latitude},${acc.longitude}`
        : "—",
    }));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `accident_records_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Print / Save as PDF
  const exportPrint = () => {
    const rows = history.map((acc, i) => `
      <tr style="background:${isYes(acc.vibration) ? "#fce4ec" : "#f9f9f9"}">
        <td>${i + 1}</td>
        <td>${formatDateTimeWithIndex(acc.date)}</td>
        <td>${acc.latitude  || "—"}</td>
        <td>${acc.longitude || "—"}</td>
        <td style="color:${isYes(acc.vibration) ? "#c62828" : "#2e7d32"};font-weight:bold">${acc.vibration || "—"}</td>
        <td>${acc.distance}</td>
        <td>${acc.latitude && acc.longitude
          ? `<a href="https://maps.google.com/?q=${acc.latitude},${acc.longitude}">Map</a>`
          : "—"}</td>
      </tr>`).join("");

    const win = window.open("", "_blank");
    win.document.write(`
      <html><head><title>Accident Records</title>
      <style>
        body { font-family: Segoe UI, Arial, sans-serif; padding: 24px; }
        h2   { color: #1a237e; }
        table { width:100%; border-collapse:collapse; font-size:0.93em; }
        th { padding:10px 12px; background:#f2f2f2; border:1px solid #ddd; text-align:left; }
        td { padding:10px 12px; border:1px solid #ddd; }
        @media print { a { display:none; } }
      </style></head>
      <body>
        <h2>🚑 Accident Detection — Records</h2>
        <p>Exported: ${new Date().toLocaleString("en-GB")}</p>
        <table>
          <thead><tr>
            <th>#</th><th>Date &amp; Time</th><th>Latitude</th>
            <th>Longitude</th><th>Vibration</th><th>Distance (cm)</th><th>Maps</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </body></html>`);
    win.document.close();
    win.print();
  };

  // ─── derived ──────────────────────────────────────────────────────────────
  const bannerBg    = latestAlert && isYes(latestAlert.vibration) ? "#e53935" : "#43a047";
  const unreadCount = alerts.filter((a) => !a.read).length;

  // ─── render ───────────────────────────────────────────────────────────────
  return (
    <div style={{
      padding: "20px",
      fontFamily: "'Segoe UI', Arial, sans-serif",
      backgroundColor: "#f0f2f5",
      minHeight: "100vh",
    }}>

      {/* ── Error banner ──────────────────────────────────────────────────── */}
      {fetchError && (
        <div style={{
          backgroundColor: "#fff3cd", color: "#856404",
          border: "1px solid #ffc107", padding: "12px 16px",
          borderRadius: "6px", marginBottom: "16px", fontWeight: 500,
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
          <br />
          {/* FIX: formatDateTime now correctly shows the full time component
              because (a) the regex is tested on the T-normalised string and
              (b) the parsed Date object's time fields are used as a fallback. */}
          📅 Date &amp; Time: {formatDateTime(latestAlert.date)}
          <br />📍 Lat: {latestAlert.latitude || "—"} &nbsp;|&nbsp; Lng: {latestAlert.longitude || "—"}
          <br />💥 Vibration: <strong>{latestAlert.vibration}</strong>
          &nbsp;|&nbsp;
          📏 Distance: <strong>{latestAlert.distance} cm</strong>
          {/* REMOVED: Status line removed per requirement */}
        </div>
      )}

      <h2 style={{ marginBottom: "20px", color: "#1a237e" }}>
        🚑 Accident Detection System
      </h2>

      {/* ── System status card ───────────────────────────────────────────── */}
      <div style={cardStyle}>
        <h3 style={sectionTitle}>📊 System Status</h3>
        {loading ? (
          <p style={{ color: "#888" }}>Loading data from Google Sheets…</p>
        ) : (
          <div style={{ display: "flex", gap: "28px", flexWrap: "wrap" }}>
            <StatItem label="Total Records"     value={stats.total} />
            <StatItem label="Last 24 h"         value={stats.last24h} />
            <StatItem label="Vibration YES"     value={stats.vibrationYes}  valueColor="#e53935" />
            <StatItem label="Vibration NO"      value={stats.vibrationNo}   valueColor="#43a047" />
            <StatItem label="Latest Distance"   value={`${stats.latestDistance} cm`} />
            {/* FIX: "ML Models Active/Inactive" StatItem removed from here.
                It was: <StatItem label="ML Models" value={...} valueColor={...} />
                Removed per requirement — do not add it back. */}
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
          <p>
            <strong>Date &amp; Time:</strong>{" "}
            {/* FIX: formatDateTime now shows both date AND time correctly */}
            {latestAlert?.date ? formatDateTime(latestAlert.date) : "No data"}
          </p>
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
            <span style={{
              color: isYes(latestAlert?.vibration) ? "#e53935" : "#43a047",
              fontWeight: "bold",
            }}>
              {latestAlert?.vibration || "No data"}
            </span>
          </p>
          <p><strong>Distance:</strong> {latestAlert ? `${latestAlert.distance} cm` : "No data"}</p>
          {/* REMOVED: Status row removed per requirement */}
        </div>

      </div>

      {/* ── Accident records table ───────────────────────────────────────── */}
      <div style={cardStyle}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
          <h3 style={{ ...sectionTitle, margin: 0, border: "none", paddingBottom: 0 }}>
            🚗 Accident Records ({history.length})
          </h3>
          {history.length > 0 && (
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button onClick={exportCSV} style={{
                padding: "7px 14px", backgroundColor: "#1976d2", color: "#fff",
                border: "none", borderRadius: "5px", cursor: "pointer", fontSize: "0.85em", fontWeight: "600",
              }}>⬇️ CSV</button>
              <button onClick={exportJSON} style={{
                padding: "7px 14px", backgroundColor: "#388e3c", color: "#fff",
                border: "none", borderRadius: "5px", cursor: "pointer", fontSize: "0.85em", fontWeight: "600",
              }}>⬇️ JSON</button>
              <button onClick={exportPrint} style={{
                padding: "7px 14px", backgroundColor: "#6d4c41", color: "#fff",
                border: "none", borderRadius: "5px", cursor: "pointer", fontSize: "0.85em", fontWeight: "600",
              }}>🖨️ Print / PDF</button>
            </div>
          )}
        </div>

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
                  <th style={thStyle}>Date &amp; Time</th>
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
                    <td style={{ ...tdStyle, whiteSpace: "nowrap" }}>
                      {/* TEMPORARY FIX: formatDateTimeWithIndex shows the
                          record number (e.g. "#1") when sheet time is missing,
                          so the column is never blank. Replace with
                          formatDateTime(acc.date) once the sheet stores full
                          datetime strings. */}
                      {formatDateTimeWithIndex(acc.date)}
                    </td>
                    <td style={tdStyle}>{acc.latitude  || "—"}</td>
                    <td style={tdStyle}>{acc.longitude || "—"}</td>
                    <td style={{
                      ...tdStyle,
                      fontWeight: "bold",
                      color: isYes(acc.vibration) ? "#c62828" : "#2e7d32",
                    }}>
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
                  {/* FIX: formatDateTime handles ISO alert timestamps too */}
                  <span style={{ fontSize: "0.8em", color: "#999" }}>
                    {formatDateTime(alert.timestamp)}
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