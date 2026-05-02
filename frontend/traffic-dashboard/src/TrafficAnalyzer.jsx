import React, { useState } from 'react';
import './TrafficAnalyzer.css';

const TrafficAnalyzer = () => {
  const [destination, setDestination] = useState('');
  const [origin, setOrigin] = useState('');
  const [useAutoLocation, setUseAutoLocation] = useState(true);
  const [loading, setLoading] = useState(false);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

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
      default: return '⚪';
    }
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
          <div className="form-group">
            <label>Starting Point</label>
            <input
              type="text"
              placeholder="e.g., Colombo Fort, Sri Lanka"
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
            placeholder="e.g., Galle Fort, Sri Lanka"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            className="route-input"
            onKeyPress={(e) => e.key === 'Enter' && analyzeRoute()}
          />
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
                  +{Math.round(analysis.primary_route.delay_minutes)} min 
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
                <p>Traffic conditions are acceptable. No significant time savings from alternative routes.</p>
              )}
            </div>
          )}

          {/* Alternative Routes */}
          {analysis.alternatives && analysis.alternatives.length > 0 && (
            <div className="alternatives-section">
              <h4>🛣️ Alternative Routes</h4>
              <div className="alternatives-grid">
                {analysis.alternatives.map((alt, index) => (
                  <div key={index} className="alternative-card">
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
