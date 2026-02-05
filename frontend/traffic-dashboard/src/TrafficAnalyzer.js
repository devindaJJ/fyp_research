import React, { useState, useEffect } from 'react';
import './TrafficAnalyzer.css';
import 'leaflet/dist/leaflet.css';
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from 'react-leaflet';

const SAMPLE_HISTORICAL_POINTS = [
  // sample points (timestamps are within last 72 hours)
  { lat: 6.9271, lon: 79.8612, intensity: 0.9, ts: new Date(Date.now() - 2 * 3600 * 1000).toISOString(), label: 'Colombo high' },
  { lat: 6.9275, lon: 79.8600, intensity: 0.7, ts: new Date(Date.now() - 3 * 3600 * 1000).toISOString(), label: 'Colombo med' },
  { lat: 6.0535, lon: 80.2210, intensity: 0.6, ts: new Date(Date.now() - 20 * 3600 * 1000).toISOString(), label: 'Galle med' },
  { lat: 7.2906, lon: 80.6337, intensity: 0.8, ts: new Date(Date.now() - 30 * 3600 * 1000).toISOString(), label: 'Kandy high' },
  { lat: 7.2096, lon: 79.8357, intensity: 0.4, ts: new Date(Date.now() - 50 * 3600 * 1000).toISOString(), label: 'Negombo low' }
];

const TrafficAnalyzer = () => {
  const [destination, setDestination] = useState('');
  const [origin, setOrigin] = useState('');
  const [useAutoLocation, setUseAutoLocation] = useState(true);

  // Autocomplete state
  const [destSuggestions, setDestSuggestions] = useState([]);
  const [originSuggestions, setOriginSuggestions] = useState([]);
  const [showDestSuggestions, setShowDestSuggestions] = useState(false);
  const [showOriginSuggestions, setShowOriginSuggestions] = useState(false);
  const destDebounceRef = React.useRef(null);
  const originDebounceRef = React.useRef(null);
  const [loading, setLoading] = useState(false);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [selectedAltIndex, setSelectedAltIndex] = useState(null);

  // Sample heatmap toggle state (frontend only, hard-coded sample points)
  const [showSampleHeat, setShowSampleHeat] = useState(false);
  const [sampleWindowHours, setSampleWindowHours] = useState(24);

  const API_BASE_URL = 'http://localhost:8000';

  // Get current location
  const fetchCurrentLocation = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/traffic/current-location`);
      const data = await response.json();
      
      if (data.success) {
        setCurrentLocation(data.location);
      } else {
        setError(data.error || 'Failed to get current location');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Analyze route
  const analyzeRoute = async () => {
    if (!destination.trim()) {
      setError('Please enter a destination');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setAnalysis(null);

      const requestBody = {
        destination: destination.includes('Sri Lanka') ? destination : `${destination}, Sri Lanka`
      };

      if (!useAutoLocation && origin.trim()) {
        requestBody.origin = origin.includes('Sri Lanka') ? origin : `${origin}, Sri Lanka`;
      }

      const response = await fetch(`${API_BASE_URL}/api/traffic/analyze-route`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (data.success) {
        setAnalysis(data.analysis);
      } else {
        setError(data.error || 'Failed to analyze route');
      }
    } catch (err) {
      setError('Network error: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const getTrafficColor = (level) => {
    switch (level) {
      case 'light': return '#4caf50';
      case 'moderate': return '#ff9800';
      case 'heavy': return '#f44336';
      default: return '#9e9e9e';
    }
  };

  const getTrafficIcon = (level) => {
    switch (level) {
      case 'light': return '🟢';
      case 'moderate': return '🟡';
      case 'heavy': return '🔴';
      case 'severe': return '🔺';
      default: return '⚪';
    }
  };

  // Decode encoded polyline (Google polyline algorithm)
  const decodePolyline = (encoded) => {
    if (!encoded) return [];
    let points = [];
    let index = 0, lat = 0, lng = 0;

    while (index < encoded.length) {
      let b, shift = 0, result = 0;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      const dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lat += dlat;

      shift = 0;
      result = 0;
      do {
        b = encoded.charCodeAt(index++) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      const dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lng += dlng;

      points.push([lat / 1e5, lng / 1e5]);
    }

    return points;
  };



  // Map subcomponent
  const RouteMap = ({ encodedPolyline, congestionLevel, delayMinutes, segments }) => {
    const [showDebug, setShowDebug] = useState(false);

    // If segments are provided, draw each segment colored by its traffic level
    const hasSegments = Array.isArray(segments) && segments.length > 0;

    const decode = (enc) => decodePolyline(enc || '');

    const allCoords = hasSegments ? segments.flatMap(s => decode(s.polyline)) : decode(encodedPolyline);
    if (!allCoords || allCoords.length === 0) return null;

    // center on midpoint
    const center = allCoords[Math.floor(allCoords.length / 2)];

    const colorForLevel = (lvl) => {
      switch ((lvl || '').toLowerCase()) {
        case 'light': return '#4caf50';
        case 'moderate': return '#ff9800';
        case 'heavy': return '#f44336';
        case 'severe': return '#b71c1c';
        default: return '#1976d2';
      }
    };

    return (
      <div>
        <MapContainer style={{ height: '360px', width: '100%', borderRadius: '8px' }} bounds={allCoords} scrollWheelZoom={false}>
          <TileLayer
            attribution='© OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Sample hard-coded historical heatmap (rendered as circle markers) */}
          {showSampleHeat && SAMPLE_HISTORICAL_POINTS.filter(p => {
            const cutoff = Date.now() - (sampleWindowHours * 3600 * 1000);
            return new Date(p.ts).getTime() >= cutoff;
          }).map((p, idx) => {
            const color = p.intensity > 0.75 ? '#d32f2f' : p.intensity > 0.5 ? '#ff9800' : '#4caf50';
            const radius = Math.max(6, Math.round(p.intensity * 14));
            return (
              <CircleMarker
                key={`sample-${idx}`}
                center={[p.lat, p.lon]}
                radius={radius}
                pathOptions={{ color, fillColor: color, fillOpacity: 0.6 }}
              >
                <Popup>
                  <div style={{ minWidth: 120 }}>
                    <strong>{p.label}</strong><br />
                    Intensity: {Math.round(p.intensity * 100)}%<br />
                    Time: {new Date(p.ts).toLocaleString()}
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

          {hasSegments ? (
            segments.map((seg, idx) => {
              const segCoords = (seg.points && seg.points.length) ? seg.points : decode(seg.polyline);
              const c = colorForLevel(seg.traffic_level);
              if (!segCoords || segCoords.length === 0) return null;
              return (
                <Polyline
                  key={idx}
                  positions={segCoords}
                  pathOptions={{ color: c, weight: 6, opacity: 0.9 }}
                >
                  <Popup>
                    <div style={{ minWidth: 160 }}>
                      <strong>Traffic:</strong> {String(seg.traffic_level).toUpperCase()}<br />
                      <strong>Delay:</strong> {Math.round(seg.delay_minutes || 0) > 0 ? `+${Math.round(seg.delay_minutes || 0)}` : Math.round(seg.delay_minutes || 0)} min<br />
                      <small>{seg.distance || ''}</small>
                    </div>
                  </Popup>
                </Polyline>
              );
            })
          ) : (
            <Polyline positions={decode(encodedPolyline)} pathOptions={{ color: colorForLevel(congestionLevel), weight: 6, opacity: 0.85 }} />
          )}


          {/* Start / End */}
          <CircleMarker center={allCoords[0]} radius={6} pathOptions={{ color: '#1976d2', fillColor: '#1976d2', fillOpacity: 1 }}>
            <Popup>Start: {analysis.origin}</Popup>
          </CircleMarker>

          <CircleMarker center={allCoords[allCoords.length - 1]} radius={6} pathOptions={{ color: '#1976d2', fillColor: '#1976d2', fillOpacity: 1 }}>
            <Popup>End: {analysis.destination}</Popup>
          </CircleMarker>

        </MapContainer>

        <div style={{ marginTop: 8, display: 'flex', gap: 12, alignItems: 'center' }}>
          <strong>Traffic on route:</strong>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div style={{ width: 12, height: 12, background: '#4caf50', borderRadius: 2 }} /> <small>Light</small>
            <div style={{ width: 12, height: 12, background: '#ff9800', borderRadius: 2 }} /> <small>Moderate</small>
            <div style={{ width: 12, height: 12, background: '#f44336', borderRadius: 2 }} /> <small>Heavy</small>
            <div style={{ width: 12, height: 12, background: '#b71c1c', borderRadius: 2 }} /> <small>Severe</small>
          </div>

          {typeof delayMinutes === 'number' && (
            <span style={{ marginLeft: 12 }}>— Delay: {Math.round(delayMinutes) > 0 ? `+${Math.round(delayMinutes)}` : Math.round(delayMinutes)} min</span>
          )}

          <button style={{ marginLeft: 16, padding: '6px 10px', fontSize: 12 }} onClick={() => setShowDebug(!showDebug)}>
            {showDebug ? 'Hide' : 'Show'} segment debug
          </button>
        </div>

        {showDebug && segments && (
          <div style={{ marginTop: 8, background: '#fff8e1', padding: 10, borderRadius: 6 }}>
            <strong>Segments ({segments.length})</strong>
            <ul style={{ margin: '8px 0 0 16px' }}>
              {segments.map((s, i) => (
                <li key={i}>
                  #{i + 1}: {String(s.traffic_level).toUpperCase()} — +{Math.round(s.delay_minutes || 0)} min — points: {(s.points && s.points.length) || (s.polyline ? 'encoded' : 0)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="traffic-analyzer">
      <div className="traffic-header">
        <h2>🚗 Traffic Route Analyzer</h2>
        <p>Real-time traffic analysis powered by Google Maps</p>
      </div>

      {/* Location Detection */}
      <div className="location-section">
        <button 
          onClick={fetchCurrentLocation}
          className="location-btn"
          disabled={loading}
        >
          📍 {currentLocation ? 'Refresh Location' : 'Detect My Location'}
        </button>
        
        {currentLocation && (
          <div className="current-location">
            <strong>Your Location:</strong> {currentLocation.city}, {currentLocation.country}
            <br />
            <small>{currentLocation.address}</small>
          </div>
        )}
      </div>

      {/* Input Form */}
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
          <div className="form-group" style={{ position: 'relative' }}>
            <label>Starting Point</label>
            <input
              type="text"
              placeholder="e.g., Colombo Fort, Sri Lanka"
              value={origin}
              onChange={(e) => {
                const v = e.target.value;
                setOrigin(v);
                setShowOriginSuggestions(true);
                if (originDebounceRef.current) clearTimeout(originDebounceRef.current);
                originDebounceRef.current = setTimeout(() => {
                  fetch(`${API_BASE_URL}/api/traffic/location-suggestions?q=${encodeURIComponent(v)}`)
                    .then(r => r.json())
                    .then(j => { if (j.success) setOriginSuggestions(j.suggestions); })
                    .catch(() => setOriginSuggestions([]));
                }, 250);
              }}
              className="route-input"
              onBlur={() => setTimeout(() => setShowOriginSuggestions(false), 200)}
            />

            {showOriginSuggestions && originSuggestions && originSuggestions.length > 0 && (
              <div className="suggestions-list">
                {originSuggestions.map((s, i) => (
                  <div key={i} className="suggestion-item" onMouseDown={() => { setOrigin(s.label); setShowOriginSuggestions(false); }}>
                    {s.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="form-group" style={{ position: 'relative' }}>
          <label>Destination *</label>
          <input
            type="text"
            placeholder="e.g., Galle Fort, Sri Lanka"
            value={destination}
            onChange={(e) => {
              const v = e.target.value;
              setDestination(v);
              setShowDestSuggestions(true);
              if (destDebounceRef.current) clearTimeout(destDebounceRef.current);
              destDebounceRef.current = setTimeout(() => {
                fetch(`${API_BASE_URL}/api/traffic/location-suggestions?q=${encodeURIComponent(v)}`)
                  .then(r => r.json())
                  .then(j => { if (j.success) setDestSuggestions(j.suggestions); })
                  .catch(() => setDestSuggestions([]));
              }, 250);
            }}
            className="route-input"
            onKeyPress={(e) => e.key === 'Enter' && analyzeRoute()}
            onBlur={() => setTimeout(() => setShowDestSuggestions(false), 200)}
          />

          {showDestSuggestions && destSuggestions && destSuggestions.length > 0 && (
            <div className="suggestions-list">
              {destSuggestions.map((s, i) => (
                <div key={i} className="suggestion-item" onMouseDown={() => { setDestination(s.label); setShowDestSuggestions(false); }}>
                  {s.label}
                </div>
              ))}
            </div>
          )}
        </div>

        <button 
          onClick={analyzeRoute}
          className="analyze-btn"
          disabled={loading || !destination.trim()}
        >
          {loading ? '🔄 Analyzing...' : '🔍 Analyze Route'}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}

      {/* Analysis Results */}
      {analysis && (
        <div className="analysis-results">
          <div className="route-header">
            <h3>📍 Route Analysis</h3>
            <span className="analysis-time">
              {new Date(analysis.analysis_time).toLocaleString()}
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

          {/* Current Traffic Conditions */}
          <div 
            className="traffic-card primary-route"
            style={{ borderColor: getTrafficColor(analysis.congestion.level) }}
          >
            <div className="card-header">
              <h4>
                {getTrafficIcon(analysis.congestion.level)} Current Conditions
              </h4>
              <span 
                className="traffic-badge"
                style={{ backgroundColor: getTrafficColor(analysis.congestion.level) }}
              >
                {analysis.congestion.level.toUpperCase()}
              </span>
            </div>

            <div className="traffic-details">
              <div className="detail-row">
                <span className="label">Distance:</span>
                <span className="value">{analysis.primary_route.distance_text}</span>
              </div>
              <div className="detail-row">
                <span className="label">Normal Time:</span>
                <span className="value">{Math.round(analysis.primary_route.normal_duration)} min</span>
              </div>
              <div className="detail-row">
                <span className="label">Current Time:</span>
                <span className="value highlight">{Math.round(analysis.primary_route.traffic_duration)} min</span>
              </div>
              <div className="detail-row">
                <span className="label">Delay:</span>
                <span className="value delay">
                  {Math.round(analysis.primary_route.delay_minutes) > 0 ? `+${Math.round(analysis.primary_route.delay_minutes)}` : Math.round(analysis.primary_route.delay_minutes)} min 
                  ({Math.round(analysis.primary_route.delay_percentage)}%)
                </span>
              </div>
              <div className="detail-row">
                <span className="label">Route:</span>
                <span className="value small">{analysis.primary_route.summary}</span>
              </div>
            </div>
          </div>

          {/* Recommendation */}
          {analysis.recommendation && (
            <div className={`recommendation-card ${analysis.recommendation.should_reroute ? 'reroute' : 'stay'}`}>
              <h4>
                {analysis.recommendation.should_reroute ? '🔄 Recommendation: Take Alternative Route' : '✅ Recommendation: Continue on Current Route'}
              </h4>
              
              {analysis.recommendation.alternative ? (
                <div className="recommendation-details">
                  <p><strong>Alternative Route:</strong> {analysis.recommendation.alternative.summary}</p>
                  <p><strong>Time Savings:</strong> ~{Math.round(analysis.recommendation.alternative.time_savings)} minutes</p>
                  <p><strong>New Travel Time:</strong> {Math.round(analysis.recommendation.alternative.traffic_duration)} minutes</p>
                  <p>
                    <strong>Traffic Level:</strong> 
                    <span style={{ color: getTrafficColor(analysis.recommendation.alternative.traffic_level) }}>
                      {' '}{getTrafficIcon(analysis.recommendation.alternative.traffic_level)} {analysis.recommendation.alternative.traffic_level.toUpperCase()}
                    </span>
                  </p>
                </div>
              ) : (
                <div>
                  <p>Traffic conditions are acceptable. No significant time savings from alternative routes.</p>
                </div>
              )}
            </div>
          )}

          <div style={{ margin: '8px 0', display: 'flex', gap: 12, alignItems: 'center' }}>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <input type="checkbox" checked={showSampleHeat} onChange={(e) => setShowSampleHeat(e.target.checked)} /> Show sample historical heat
            </label>
            <label style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              Window:
              <select value={sampleWindowHours} onChange={(e) => setSampleWindowHours(Number(e.target.value))} style={{ marginLeft: 6 }}>
                <option value={6}>6h</option>
                <option value={12}>12h</option>
                <option value={24}>24h</option>
                <option value={48}>48h</option>
                <option value={72}>72h</option>
              </select>
            </label>
          </div>

          {/* Map: show suggested route on a live map with traffic indication */}
          {analysis && ((selectedAltIndex !== null && analysis.alternatives && analysis.alternatives[selectedAltIndex]) || (analysis.primary_route && analysis.primary_route.polyline)) && (
            <div className="route-map">
              <RouteMap
                encodedPolyline={selectedAltIndex !== null ? (analysis.alternatives[selectedAltIndex].polyline || '') : analysis.primary_route.polyline}
                congestionLevel={selectedAltIndex !== null ? (analysis.alternatives[selectedAltIndex].traffic_level || analysis.congestion.level) : analysis.congestion.level}
                delayMinutes={selectedAltIndex !== null ? (analysis.alternatives[selectedAltIndex].delay_minutes || 0) : analysis.delay_minutes}
                segments={selectedAltIndex !== null ? (analysis.alternatives[selectedAltIndex].segments || []) : analysis.primary_route.segments}
              />

              {selectedAltIndex !== null && (
                <div className="alternative-selected-info">
                  <h4>Selected Route: Route {selectedAltIndex + 1}</h4>
                  <p><strong>Summary:</strong> {analysis.alternatives[selectedAltIndex].summary}</p>
                  <p><strong>Time:</strong> {Math.round(analysis.alternatives[selectedAltIndex].traffic_duration)} min</p>
                  <p><strong>Distance:</strong> {analysis.alternatives[selectedAltIndex].distance_text}</p>
                  <p><strong>Traffic:</strong> {String(analysis.alternatives[selectedAltIndex].traffic_level).toUpperCase()} {analysis.alternatives[selectedAltIndex].delay_minutes > 0 ? `— +${Math.round(analysis.alternatives[selectedAltIndex].delay_minutes)} min` : ''}</p>
                </div>
              )}
            </div>
          )}

          {/* Alternative Routes */}
          {analysis.alternatives && analysis.alternatives.length > 0 && (
            <div className="alternatives-section">
              <h4>🛣️ Alternative Routes</h4>
              <div className="alternatives-grid">
                {analysis.alternatives.map((alt, index) => (
                  <div 
                    key={index} 
                    className={`alternative-card ${selectedAltIndex === index ? 'selected' : ''}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedAltIndex(selectedAltIndex === index ? null : index)}
                    onKeyPress={(e) => { if (e.key === 'Enter') setSelectedAltIndex(selectedAltIndex === index ? null : index); }}
                  >
                    <div className="alt-header">
                      <span className="alt-number">Route {index + 1}</span>
                      <span 
                        className="alt-badge"
                        style={{ backgroundColor: getTrafficColor(alt.traffic_level) }}
                      >
                        {getTrafficIcon(alt.traffic_level)}
                      </span>
                    </div>
                    <p className="alt-summary">{alt.summary}</p>
                    <div className="alt-details">
                      <div>⏱️ {Math.round(alt.traffic_duration)} min</div>
                      <div>📏 {alt.distance_text}</div>
                      {alt.delay_minutes > 0 && (
                        <div className="alt-delay">+{Math.round(alt.delay_minutes)} min delay</div>
                      )}
                    </div>
                    <div style={{ marginTop: 10 }}>
                      <button className="view-route-btn" onClick={(ev) => { ev.stopPropagation(); setSelectedAltIndex(selectedAltIndex === index ? null : index); }}>
                        {selectedAltIndex === index ? 'Hide on Map' : 'View on Map'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TrafficAnalyzer;
