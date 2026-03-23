import React, { useState, useMemo, useEffect } from 'react';
const API_URL = "http://localhost:8000/api";
import './ParkingDetails.css';

// Icons (you can use react-icons or emojis)
const Icons = {
  Car: '🚗',
  Parking: '🅿️',
  Clock: '🕒',
  Signal: '📶',
  Location: '📍',
  Export: '📤',
  Search: '🔍',
  Filter: '⚙️',
  Close: '✕',
  Refresh: '🔄',
  Chart: '📊',
  Alert: '⚠️',
  Check: '✓',
  Sensor: '📡',
  Gauge: '🔧',
  Trending: '📈',
  Eye: '👁️',
  SensorGood: '🟢',
  SensorWarn: '🟡',
  SensorBad: '🔴'
};

const PAGE_SIZE = 12;

// Utility functions for sensor health and confidence scoring
const SensorUtils = {
  // Calculate confidence score based on multiple factors
  calculateConfidence: (data) => {
    let score = 50; // Base score
    
    // Sensor type and data source quality
    if (data.sensor_types && Array.isArray(data.sensor_types)) {
      score += Math.min(data.sensor_types.length * 15, 30); // Multi-sensor fusion
    }
    
    // Signal strength (RSSI)
    if (data.rssi !== undefined && data.rssi !== null) {
      const rssi = parseInt(data.rssi);
      if (rssi >= -70) score += 20;
      else if (rssi >= -85) score += 10;
    }
    
    // Data freshness
    if (data.timestamp) {
      const age = (Date.now() - new Date(data.timestamp).getTime()) / 1000;
      if (age < 60) score += 15;
      else if (age < 300) score += 8;
    }
    
    // Consistency across multiple sensors
    if (data.multi_sensor_agreement !== undefined) {
      score += data.multi_sensor_agreement * 20;
    }
    
    // Calibration status
    if (data.sensor_calibrated === true) {
      score += 10;
    } else if (data.sensor_calibrated === false) {
      score -= 15;
    }
    
    return Math.min(Math.max(score, 0), 100);
  },

  // Get confidence level label and color
  getConfidenceLevel: (score) => {
    if (score >= 85) return { level: 'EXCELLENT', color: '#10b981', bg: '#d1fae5', icon: '⭐' };
    if (score >= 70) return { level: 'GOOD', color: '#3b82f6', bg: '#dbeafe', icon: '✓' };
    if (score >= 50) return { level: 'FAIR', color: '#f59e0b', bg: '#fef3c7', icon: '⚠️' };
    return { level: 'POOR', color: '#ef4444', bg: '#fee2e2', icon: '✗' };
  },

  // Detect anomalies in sensor data
  detectAnomalies: (data, historicalData = []) => {
    const anomalies = [];
    
    if (!data.distance) return anomalies;
    
    const distance = parseFloat(data.distance);
    
    // Check for impossible readings
    if (distance < 0 || distance > 500) {
      anomalies.push({ type: 'RANGE_VIOLATION', severity: 'high', msg: 'Distance outside valid range' });
    }
    
    // Check for sudden jumps
    if (historicalData.length > 0) {
      const prevDistance = parseFloat(historicalData[historicalData.length - 1].distance) || 0;
      const jump = Math.abs(distance - prevDistance);
      if (jump > 100) {
        anomalies.push({ type: 'SUDDEN_CHANGE', severity: 'medium', msg: 'Sudden sensor reading change' });
      }
    }
    
    // Check signal strength
    if (data.rssi && parseInt(data.rssi) < -95) {
      anomalies.push({ type: 'WEAK_SIGNAL', severity: 'medium', msg: 'Weak signal - may affect accuracy' });
    }
    
    // Check calibration
    if (data.sensor_calibrated === false) {
      anomalies.push({ type: 'UNCALIBRATED', severity: 'high', msg: 'Sensor not calibrated' });
    }
    
    return anomalies;
  }
};

function Badge({ status, size = 'medium', confidence = null }) {
  const s = (status || '').toString().toLowerCase().trim();
  const sizeClass = `badge-${size}`;
  
  const config = {
    occupied: { text: 'OCCUPIED', color: '#ef4444', bg: '#fee2e2', icon: '🔴' },
    vacant: { text: 'VACANT', color: '#10b981', bg: '#d1fae5', icon: '🟢' },
    parked: { text: 'PARKED', color: '#f59e0b', bg: '#fef3c7', icon: '🟡' },
    empty: { text: 'EMPTY', color: '#6b7280', bg: '#f3f4f6', icon: '⚫' },
    close_parking: { text: 'CLOSE', color: '#dc2626', bg: '#fecaca', icon: '🚨' },
    normal_parking: { text: 'NORMAL', color: '#f97316', bg: '#fed7aa', icon: '🟠' },
    far_parking: { text: 'FAR', color: '#eab308', bg: '#fef08a', icon: '🟡' }
  };
  
  const cfg = config[s] || { text: s.toUpperCase() || 'UNKNOWN', color: '#6b7280', bg: '#f3f4f6', icon: '❓' };
  
  return (
    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
      <span 
        className={`status-badge ${sizeClass}`}
        style={{
          backgroundColor: cfg.bg,
          color: cfg.color,
          border: `1px solid ${cfg.color}20`,
          padding: '4px 12px',
          borderRadius: '20px',
          fontWeight: '600',
          fontSize: size === 'small' ? '0.75rem' : '0.875rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px'
        }}
      >
        {cfg.icon && <span>{cfg.icon}</span>}
        {cfg.text}
      </span>
      {confidence !== null && (
        <ConfidenceBadge score={confidence} size={size} />
      )}
    </div>
  );
}

function ConfidenceBadge({ score, size = 'medium' }) {
  const conf = SensorUtils.getConfidenceLevel(score);
  return (
    <span title={`Confidence: ${conf.level}`}
      style={{
        backgroundColor: conf.bg,
        color: conf.color,
        border: `1px solid ${conf.color}40`,
        padding: size === 'small' ? '2px 8px' : '4px 10px',
        borderRadius: '16px',
        fontWeight: '600',
        fontSize: size === 'small' ? '0.7rem' : '0.8rem',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '3px',
        whiteSpace: 'nowrap'
      }}
    >
      <span>{conf.icon}</span>
      <span>{score}%</span>
    </span>
  );
}

function SensorHealthIndicator({ data }) {
  const confidence = SensorUtils.calculateConfidence(data);
  const conf = SensorUtils.getConfidenceLevel(confidence);
  const anomalies = SensorUtils.detectAnomalies(data);
  
  return (
    <div style={{
      background: conf.bg,
      border: `1px solid ${conf.color}40`,
      borderRadius: '8px',
      padding: '8px 12px',
      fontSize: '12px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
        <span style={{ fontSize: '14px' }}>{conf.icon}</span>
        <span style={{ fontWeight: '600', color: conf.color }}>
          {conf.level} (${confidence}%)
        </span>
      </div>
      
      {data.sensor_types && (
        <div style={{ fontSize: '11px', color: '#555', marginBottom: '4px' }}>
          {Icons.Sensor} Sensors: {Array.isArray(data.sensor_types) ? data.sensor_types.join(', ') : data.sensor_types}
        </div>
      )}
      
      {data.sensor_calibrated !== undefined && (
        <div style={{ fontSize: '11px', color: '#555', marginBottom: '4px' }}>
          {Icons.Gauge} Calibration: {data.sensor_calibrated ? '✓ Done' : '✗ Needed'}
        </div>
      )}
      
      {anomalies.length > 0 && (
        <div style={{ marginTop: '6px', borderTop: `1px solid ${conf.color}20`, paddingTop: '6px' }}>
          {anomalies.map((a, i) => (
            <div key={i} style={{ 
              fontSize: '11px', 
              color: a.severity === 'high' ? '#dc2626' : '#f59e0b',
              display: 'flex',
              gap: '4px',
              marginBottom: i < anomalies.length - 1 ? '3px' : '0'
            }}>
              <span>•</span>
              <span><strong>{a.type}:</strong> {a.msg}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value, change, icon, color = '#3b82f6' }) {
  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <div className="stat-card-icon" style={{ backgroundColor: `${color}20`, color }}>
          {icon}
        </div>
        <div className="stat-card-title">{title}</div>
      </div>
      <div className="stat-card-value">{value}</div>
      {change && (
        <div className="stat-card-change" style={{ color: change > 0 ? '#10b981' : '#ef4444' }}>
          {change > 0 ? '+' : ''}{change}%
        </div>
      )}
    </div>
  );
}

function ParkingCard({ data, onClick }) {
  const duration = data.parking_duration ? `${data.parking_duration}s` : '-';
  const isRecent = Date.now() - new Date(data.timestamp).getTime() < 300000; // 5 minutes
  const confidence = SensorUtils.calculateConfidence(data);
  const anomalies = SensorUtils.detectAnomalies(data);
  
  return (
    <div 
      className={`parking-card ${isRecent ? 'recent' : ''} ${data.status?.toLowerCase() === 'occupied' ? 'occupied' : ''}`}
      onClick={() => onClick(data)}
      style={{ 
        borderLeft: anomalies.length > 0 ? '4px solid #ef4444' : confidence < 60 ? '4px solid #f59e0b' : '4px solid #10b981'
      }}
    >
      <div className="parking-card-header">
        <div className="parking-card-location">
          <span className="location-icon">{Icons.Location}</span>
          <div>
            <h4>{data.location || 'Unknown Location'}</h4>
            <p className="spot-id">{data.parking_spot_id || data.device_id || 'N/A'}</p>
          </div>
        </div>
        <Badge status={data.status} confidence={confidence} />
      </div>
      
      <div className="parking-card-body">
        <div className="metric-row">
          <div className="metric">
            <span className="metric-icon">{Icons.Car}</span>
            <div>
              <div className="metric-value">{data.distance ? `${data.distance} cm` : '-'}</div>
              <div className="metric-label">Distance</div>
            </div>
          </div>
          <div className="metric">
            <span className="metric-icon">{Icons.Clock}</span>
            <div>
              <div className="metric-value">{duration}</div>
              <div className="metric-label">Duration</div>
            </div>
          </div>
          <div className="metric">
            <span className="metric-icon">{Icons.Signal}</span>
            <div>
              <div className="metric-value">{data.rssi || '-'}</div>
              <div className="metric-label">Signal</div>
            </div>
          </div>
        </div>
        
        {data.sensor_types && (
          <div style={{ 
            background: '#f0f9ff', 
            border: '1px solid #bfdbfe', 
            borderRadius: '6px', 
            padding: '8px',
            marginTop: '8px',
            fontSize: '12px',
            color: '#0c4a6e'
          }}>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>{Icons.Sensor} Multi-Sensor Data:</div>
            <div>{Array.isArray(data.sensor_types) ? data.sensor_types.join(', ') : data.sensor_types}</div>
          </div>
        )}
        
        {anomalies.length > 0 && (
          <div style={{
            background: '#fef2f2',
            border: '1px solid #fca5a5',
            borderRadius: '6px',
            padding: '8px',
            marginTop: '8px',
            fontSize: '11px',
            color: '#7f1d1d'
          }}>
            <div style={{ fontWeight: '600', marginBottom: '4px' }}>{Icons.Alert} Anomalies Detected:</div>
            {anomalies.map((a, i) => (
              <div key={i}>• {a.type}: {a.msg}</div>
            ))}
          </div>
        )}
        
        {data.zone && (
          <div className="zone-indicator">
            <span>Zone:</span>
            <span className="zone-tag">{data.zone}</span>
          </div>
        )}
      </div>
      
      <div className="parking-card-footer">
        <span className="timestamp">{new Date(data.timestamp).toLocaleTimeString()}</span>
        {isRecent && <span className="live-indicator">● LIVE</span>}
      </div>
    </div>
  );
}

function FilterPanel({ filters, setFilters, onApply }) {
  const [localFilters, setLocalFilters] = useState(filters);
  
  const statusOptions = [
    { value: '', label: 'All Status' },
    { value: 'occupied', label: 'Occupied' },
    { value: 'vacant', label: 'Vacant' },
    { value: 'parked', label: 'Parked' },
    { value: 'empty', label: 'Empty' }
  ];
  
  const zoneOptions = [
    { value: '', label: 'All Zones' },
    { value: 'ZONE_A', label: 'Zone A' },
    { value: 'ZONE_B', label: 'Zone B' },
    { value: 'ZONE_C', label: 'Zone C' },
    { value: 'ZONE_D', label: 'Zone D' }
  ];

  const confidenceOptions = [
    { value: '', label: 'All Confidence Levels' },
    { value: '85', label: 'Excellent (≥85%)' },
    { value: '70', label: 'Good (≥70%)' },
    { value: '50', label: 'Fair (≥50%)' },
    { value: '0', label: 'Show Poor Data' }
  ];

  const sensorHealthOptions = [
    { value: '', label: 'All Sensors' },
    { value: 'good', label: 'Good Health' },
    { value: 'fair', label: 'Fair Health' },
    { value: 'poor', label: 'Poor Health' },
    { value: 'uncalibrated', label: 'Uncalibrated' }
  ];
  
  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h4>{Icons.Filter} Filters</h4>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div className="filter-group">
          <label>Status</label>
          <select 
            value={localFilters.status || ''}
            onChange={(e) => setLocalFilters({...localFilters, status: e.target.value})}
          >
            {statusOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Confidence Level</label>
          <select 
            value={localFilters.minConfidence || ''}
            onChange={(e) => setLocalFilters({...localFilters, minConfidence: e.target.value})}
          >
            {confidenceOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div className="filter-group">
          <label>Zone</label>
          <select 
            value={localFilters.zone || ''}
            onChange={(e) => setLocalFilters({...localFilters, zone: e.target.value})}
          >
            {zoneOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Sensor Health</label>
          <select 
            value={localFilters.sensorHealth || ''}
            onChange={(e) => setLocalFilters({...localFilters, sensorHealth: e.target.value})}
          >
            {sensorHealthOptions.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="filter-group">
        <label>Distance Range (cm)</label>
        <div className="range-inputs">
          <input 
            type="number" 
            placeholder="Min" 
            value={localFilters.distanceMin || ''}
            onChange={(e) => setLocalFilters({...localFilters, distanceMin: e.target.value})}
          />
          <span>to</span>
          <input 
            type="number" 
            placeholder="Max" 
            value={localFilters.distanceMax || ''}
            onChange={(e) => setLocalFilters({...localFilters, distanceMax: e.target.value})}
          />
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <div className="filter-group">
          <label>Time Range</label>
          <select 
            value={localFilters.timeRange || ''}
            onChange={(e) => setLocalFilters({...localFilters, timeRange: e.target.value})}
          >
            <option value="">All Time</option>
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
        </div>

        <div className="filter-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <input 
              type="checkbox" 
              checked={localFilters.showAnomaliesOnly || false}
              onChange={(e) => setLocalFilters({...localFilters, showAnomaliesOnly: e.target.checked})}
            />
            Show Anomalies Only
          </label>
        </div>
      </div>
      
      <div className="filter-actions">
        <button className="btn-secondary" onClick={() => setLocalFilters({ 
          status: '', 
          zone: '', 
          distanceMin: '', 
          distanceMax: '', 
          timeRange: '',
          minConfidence: '',
          sensorHealth: '',
          showAnomaliesOnly: false
        })}>
          Clear All
        </button>
        <button className="btn-primary" onClick={() => {
          setFilters(localFilters); 
          onApply();
        }}>
          Apply Filters
        </button>
      </div>
    </div>
  );
}

const ParkingDetails = () => {
  const [parkingData, setParkingData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [view, setView] = useState('cards'); // 'cards' or 'table' or 'grid'
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [filters, setFilters] = useState({
    status: '',
    zone: '',
    distanceMin: '',
    distanceMax: '',
    timeRange: '',
    minConfidence: '',
    sensorHealth: '',
    showAnomaliesOnly: false
  });
  const [stats, setStats] = useState({ 
    total: 0, 
    occupied: 0, 
    vacant: 0, 
    avgDuration: 0,
    avgConfidence: 0,
    highQuality: 0,
    anomalies: 0 
  });

  // Fetch parking data from backend
  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/parking-data`)
      .then(res => res.json())
      .then(data => {
        if (data.success && Array.isArray(data.data)) {
          setParkingData(data.data);
          setError(null);
        } else {
          setParkingData([]);
          setError(data.error || 'Failed to fetch parking data');
        }
        setLoading(false);
      })
      .catch(err => {
        setParkingData([]);
        setError(err.message || 'Network error');
        setLoading(false);
      });
  }, []);

  // Calculate statistics
  useEffect(() => {
    const validData = parkingData.filter(d => d.timestamp);
    const occupied = validData.filter(d => d.status?.toLowerCase().includes('occupied') || d.vehicle_detected === 'YES');
    const durations = validData.map(d => parseInt(d.parking_duration) || 0).filter(d => d > 0);
    const avgDuration = durations.length > 0 
      ? Math.round(durations.reduce((a, b) => a + b) / durations.length) 
      : 0;
    
    // Calculate confidence metrics
    const confidenceScores = validData.map(d => SensorUtils.calculateConfidence(d));
    const avgConfidence = confidenceScores.length > 0
      ? Math.round(confidenceScores.reduce((a, b) => a + b) / confidenceScores.length)
      : 0;
    
    const highQuality = confidenceScores.filter(c => c >= 70).length;
    
    // Count anomalies
    let anomalyCount = 0;
    validData.forEach(d => {
      const anomalies = SensorUtils.detectAnomalies(d);
      anomalyCount += anomalies.length;
    });
    
    setStats({
      total: validData.length,
      occupied: occupied.length,
      vacant: validData.length - occupied.length,
      avgDuration,
      avgConfidence,
      highQuality,
      anomalies: anomalyCount
    });
  }, [parkingData]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = (parkingData || []).slice();
    
    // Apply search query
    if (q) {
      list = list.filter(r => (
        (r.device_id || r.device || '').toString().toLowerCase().includes(q) ||
        (r.location || '').toString().toLowerCase().includes(q) ||
        (r.parking_spot_id || r.spot_id || '').toString().toLowerCase().includes(q) ||
        (r.zone || '').toString().toLowerCase().includes(q)
      ));
    }
    
    // Apply status filter
    if (filters.status) {
      list = list.filter(r => r.status?.toLowerCase().includes(filters.status.toLowerCase()));
    }
    
    // Apply zone filter
    if (filters.zone) {
      list = list.filter(r => r.zone === filters.zone);
    }
    
    // Apply distance range filter
    if (filters.distanceMin) {
      const min = parseFloat(filters.distanceMin);
      list = list.filter(r => parseFloat(r.distance) >= min);
    }
    
    if (filters.distanceMax) {
      const max = parseFloat(filters.distanceMax);
      list = list.filter(r => parseFloat(r.distance) <= max);
    }
    
    // Apply time range filter
    if (filters.timeRange) {
      const now = new Date();
      const cutoff = new Date(now);
      
      switch(filters.timeRange) {
        case '1h': cutoff.setHours(now.getHours() - 1); break;
        case '6h': cutoff.setHours(now.getHours() - 6); break;
        case '24h': cutoff.setDate(now.getDate() - 1); break;
        case '7d': cutoff.setDate(now.getDate() - 7); break;
        default: break;
      }
      
      list = list.filter(r => new Date(r.timestamp) >= cutoff);
    }
    
    // Apply confidence filter
    if (filters.minConfidence) {
      const minConf = parseInt(filters.minConfidence);
      list = list.filter(r => {
        const conf = SensorUtils.calculateConfidence(r);
        return conf >= minConf;
      });
    }
    
    // Apply sensor health filter
    if (filters.sensorHealth) {
      list = list.filter(r => {
        const conf = SensorUtils.calculateConfidence(r);
        switch(filters.sensorHealth) {
          case 'good': return conf >= 70;
          case 'fair': return conf >= 50 && conf < 70;
          case 'poor': return conf < 50;
          case 'uncalibrated': return r.sensor_calibrated === false;
          default: return true;
        }
      });
    }
    
    // Apply anomalies filter
    if (filters.showAnomaliesOnly) {
      list = list.filter(r => {
        const anomalies = SensorUtils.detectAnomalies(r);
        return anomalies.length > 0;
      });
    }
    
    // Sort newest first
    list.sort((a,b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
    return list;
  }, [parkingData, query, filters]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const exportCSV = () => {
    const rows = filtered.map(r => {
      const confidence = SensorUtils.calculateConfidence(r);
      const anomalies = SensorUtils.detectAnomalies(r);
      return [
        r.timestamp || '',
        r.device_id || r.device || '',
        r.location || '',
        r.distance || '',
        r.vehicle_detected || '',
        r.parking_duration || '',
        r.zone || '',
        r.status || '',
        confidence,
        r.sensor_types ? (Array.isArray(r.sensor_types) ? r.sensor_types.join(';') : r.sensor_types) : '',
        r.sensor_calibrated === undefined ? 'Unknown' : (r.sensor_calibrated ? 'Yes' : 'No'),
        anomalies.length > 0 ? anomalies.map(a => a.type).join(';') : 'None',
        r.rssi || '',
        r.latitude || r.lat || '',
        r.longitude || r.lon || ''
      ];
    });
    const header = [
      'Timestamp',
      'Device ID',
      'Location',
      'Distance (cm)',
      'Vehicle Detected',
      'Duration (s)',
      'Zone',
      'Status',
      'Confidence Score (%)',
      'Sensor Types',
      'Calibrated',
      'Anomalies Detected',
      'Signal Strength (RSSI)',
      'Latitude',
      'Longitude'
    ];
    const csv = [header, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `parking_data_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const refreshData = () => {
    // Implement your data refresh logic here
    window.location.reload();
  };

  return (
    <div style={{ padding: '32px 24px', background: '#f4f6fa', minHeight: '100vh', fontFamily: 'Inter, Arial, sans-serif' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ fontWeight: 800, fontSize: 28, margin: 0, color: '#22223b' }}>
            <span style={{ marginRight: 8 }}>{Icons.Parking}</span>Smart Parking Dashboard
          </h2>
          <div style={{ fontSize: 15, color: '#555', marginTop: 4 }}>Live parking status and analytics</div>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 8, padding: '8px 16px', fontWeight: 600, cursor: 'pointer', boxShadow: '0 1px 4px #0001' }} onClick={() => window.location.reload()}>{Icons.Refresh} Refresh</button>
        </div>
      </div>

      {/* Stats Cards */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
        gap: '16px', 
        marginBottom: '32px',
        padding: '0 4px'
      }}>
        {/* Total Spots Card */}
        <div style={{
          background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(59, 130, 246, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }} 
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            📊
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            Total Spots
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline'
          }}>
            {stats.total}
            <div style={{
              fontSize: '14px',
              marginLeft: '8px',
              padding: '2px 8px',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              fontWeight: '600'
            }}>
              100%
            </div>
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Maximum capacity
          </div>
        </div>

        {/* Occupied Card */}
        <div style={{
          background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(239, 68, 68, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            🚗
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            Occupied
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px'
          }}>
            {stats.occupied}
            <div style={{
              fontSize: '14px',
              padding: '2px 8px',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span style={{ fontSize: '12px' }}>▲</span> {stats.total > 0 ? Math.round((stats.occupied / stats.total) * 100) : 0}%
            </div>
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            {stats.total > 0 ? Math.round((stats.occupied / stats.total) * 100) : 0}% of total
          </div>
        </div>

        {/* Vacant Card */}
        <div style={{
          background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(16, 185, 129, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            🅿️
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            Vacant
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px'
          }}>
            {stats.vacant}
            <div style={{
              fontSize: '14px',
              padding: '2px 8px',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span style={{ fontSize: '12px' }}>▲</span> {stats.total > 0 ? Math.round((stats.vacant / stats.total) * 100) : 0}%
            </div>
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Available for parking
          </div>
        </div>

        {/* Confidence Quality Card */}
        <div style={{
          background: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            {Icons.Eye}
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            Avg Confidence
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline'
          }}>
              {stats.avgConfidence}
            <div style={{
              fontSize: '14px',
              marginLeft: '8px',
              padding: '2px 8px',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              fontWeight: '600'
            }}>
              %
            </div>
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Detection reliability score
          </div>
        </div>

        {/* Data Quality Card */}
        <div style={{
          background: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(6, 182, 212, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            ✓
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            High Quality
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline',
            gap: '8px'
          }}>
            {stats.highQuality}
            <div style={{
              fontSize: '14px',
              padding: '2px 8px',
              background: 'rgba(255, 255, 255, 0.2)',
              borderRadius: '12px',
              fontWeight: '600'
            }}>
              ≥70%
            </div>
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Records with good/excellent confidence
          </div>
        </div>

        {/* Anomalies Card */}
        <div style={{
          background: 'linear-gradient(135deg, #ec4899 0%, #be185d 100%)',
          borderRadius: '16px',
          padding: '24px',
          color: 'white',
          boxShadow: '0 4px 20px rgba(236, 72, 153, 0.3)',
          position: 'relative',
          overflow: 'hidden',
          transition: 'transform 0.3s ease, box-shadow 0.3s ease',
          cursor: 'pointer'
        }}
        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-4px)'}
        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}>
          <div style={{ 
            position: 'absolute', 
            top: '12px', 
            right: '16px',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px'
          }}>
            {Icons.Alert}
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
            Anomalies
          </div>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: '700',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'baseline'
          }}>
            {stats.anomalies}
          </div>
          <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
            Issues detected
          </div>
        </div>
      </div>

      {/* Search and View Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px #0001', padding: '6px 14px', flex: 1, minWidth: '220px' }}>
          <span style={{ fontSize: 18, color: '#3b82f6' }}>{Icons.Search}</span>
          <input style={{ border: 'none', outline: 'none', fontSize: 15, background: 'transparent', flex: 1 }} placeholder="Search by location, device ID, or zone..." value={query} onChange={e => { setQuery(e.target.value); setPage(0); }} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button 
            style={{ background: showFilters ? '#3b82f6' : '#fff', color: showFilters ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} 
            onClick={() => setShowFilters(!showFilters)}
            title="Toggle advanced filters"
          >
            {Icons.Filter} Filters
          </button>
          <button 
            style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} 
            onClick={exportCSV}
            title="Export data as CSV with confidence scores"
          >
            {Icons.Export} Export
          </button>
          <button style={{ background: view === 'cards' ? '#3b82f6' : '#fff', color: view === 'cards' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('cards')}>Cards</button>
          <button style={{ background: view === 'grid' ? '#3b82f6' : '#fff', color: view === 'grid' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('grid')}>Grid</button>
          <button style={{ background: view === 'table' ? '#3b82f6' : '#fff', color: view === 'table' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('table')}>Table</button>
          <span style={{ fontSize: 14, color: '#555' }}>{filtered.length} records</span>
        </div>
      </div>

      {/* Advanced Filters */}
      {showFilters && (
        <div style={{ marginBottom: '20px' }}>
          <FilterPanel 
            filters={filters} 
            setFilters={setFilters}
            onApply={() => setPage(0)}
          />
        </div>
      )}

      {/* Main Content */}
      <div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: 60, color: '#888' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>{Icons.Parking}</div>
            <h3 style={{ fontWeight: 700, fontSize: 22 }}>No parking data found</h3>
            <p style={{ color: '#888', marginBottom: 18 }}>Try adjusting your search or filters</p>
            <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 8, padding: '8px 20px', fontWeight: 600, cursor: 'pointer' }} onClick={() => { 
              setQuery(''); 
              setFilters({ 
                status: '', 
                zone: '', 
                distanceMin: '', 
                distanceMax: '', 
                timeRange: '',
                minConfidence: '',
                sensorHealth: '',
                showAnomaliesOnly: false
              }); 
            }}>Clear all filters</button>
          </div>
        ) : view === 'cards' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
            {current.map((record, i) => (
              <div key={i} style={{ background: '#fff', borderRadius: 16, boxShadow: '0 2px 8px #0001', padding: 24, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 160, position: 'relative', borderLeft: record.status?.toLowerCase() === 'occupied' ? '4px solid #ef4444' : '4px solid #10b981' }} onClick={() => setSelected(record)}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontWeight: 700, fontSize: 18 }}>{record.location || 'Unknown Location'}</div>
                  <Badge status={record.status} />
                </div>
                <div style={{ fontSize: 13, color: '#555' }}>Device: {record.device_id || record.device || 'N/A'}</div>
                <div style={{ display: 'flex', gap: 18, marginTop: 8 }}>
                  <div style={{ fontSize: 13 }}>Distance: <b>{record.distance} cm</b></div>
                  <div style={{ fontSize: 13 }}>Duration: <b>{record.parking_duration || '-'}s</b></div>
                  <div style={{ fontSize: 13 }}>Zone: <b>{record.zone || '-'}</b></div>
                </div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>Time: {record.timestamp ? new Date(record.timestamp).toLocaleString() : '-'}</div>
              </div>
            ))}
          </div>
        ) : view === 'grid' ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
            {current.map((record, i) => {
              const confidence = SensorUtils.calculateConfidence(record);
              return (
                <div key={i} style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px #0001', padding: 14, minHeight: 80, display: 'flex', flexDirection: 'column', gap: 6, cursor: 'pointer' }} onClick={() => setSelected(record)}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Badge status={record.status} size="small" confidence={confidence} />
                    <span style={{ fontSize: 12, color: '#888' }}>{new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{record.location}</div>
                  <div style={{ fontSize: 12, color: '#555' }}>Distance: {record.distance} cm</div>
                  <div style={{ fontSize: 12, color: '#555' }}>Duration: {record.parking_duration || '0'}s</div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px #0001', padding: 0, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
              <thead>
                <tr style={{ background: '#f4f6fa', color: '#222', fontWeight: 700 }}>
                  <th style={{ padding: '10px 8px', textAlign: 'left' }}>Time</th>
                  <th style={{ textAlign: 'left' }}>Location</th>
                  <th style={{ textAlign: 'left' }}>Device ID</th>
                  <th style={{ textAlign: 'left' }}>Distance</th>
                  <th style={{ textAlign: 'left' }}>Duration</th>
                  <th style={{ textAlign: 'left' }}>Status</th>
                  <th style={{ textAlign: 'left' }}>Confidence</th>
                  <th style={{ textAlign: 'left' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {current.map((record, i) => {
                  const confidence = SensorUtils.calculateConfidence(record);
                  return (
                    <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f4f6fa', borderBottom: '1px solid #e0e7ef' }}>
                      <td style={{ padding: '8px 6px' }}>{new Date(record.timestamp).toLocaleString()}</td>
                      <td><strong>{record.location}</strong></td>
                      <td><code style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px', fontSize: '12px' }}>{record.device_id || record.device}</code></td>
                      <td>{record.distance} cm</td>
                      <td>{record.parking_duration || '0'}s</td>
                      <td><Badge status={record.status} size="small" /></td>
                      <td><ConfidenceBadge score={confidence} size="small" /></td>
                      <td>
                        <button style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '4px 12px', fontWeight: 600, cursor: 'pointer', fontSize: '12px' }} onClick={() => setSelected(record)}>
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {filtered.length > 0 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 32, gap: 16 }}>
          <div style={{ fontSize: 14, color: '#555' }}>
            Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} records
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} disabled={page <= 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Previous</button>
            {Array.from({ length: Math.min(5, pageCount) }, (_, i) => {
              let pageNum;
              if (pageCount <= 5) {
                pageNum = i;
              } else if (page < 2) {
                pageNum = i;
              } else if (page > pageCount - 3) {
                pageNum = pageCount - 5 + i;
              } else {
                pageNum = page - 2 + i;
              }
              return (
                <button key={pageNum} style={{ background: page === pageNum ? '#3b82f6' : '#fff', color: page === pageNum ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 12px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setPage(pageNum)} disabled={pageNum >= pageCount}>{pageNum + 1}</button>
              );
            })}
            {pageCount > 5 && <span style={{ color: '#888', fontSize: 15, margin: '0 6px' }}>...</span>}
            <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} disabled={page >= pageCount - 1} onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))}>Next</button>
          </div>
        </div>
      )}

      {/* Record Details Modal */}
      {selected && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: '#0008', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', overflowY: 'auto' }} onClick={() => setSelected(null)}>
          <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 4px 24px #0003', padding: 32, minWidth: 340, maxWidth: 500, width: '100%', position: 'relative', margin: '20px auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h3 style={{ fontWeight: 800, fontSize: 22, margin: 0 }}>Parking Record Details</h3>
              <button style={{ background: 'none', border: 'none', fontSize: 22, color: '#888', cursor: 'pointer' }} onClick={() => setSelected(null)}>{Icons.Close}</button>
            </div>

            {/* Sensor Health Section */}
            <div style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #e0e7ef' }}>
              <h4 style={{ margin: '0 0 12px 0', color: '#222', fontSize: '14px', fontWeight: '600' }}>{Icons.Sensor} Sensor Health & Confidence</h4>
              <SensorHealthIndicator data={selected} />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 18 }}>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Location</div>
                <div style={{ fontWeight: 600 }}>{selected.location}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Device ID</div>
                <div style={{ fontWeight: 600 }}>{selected.device_id || selected.device}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Status</div>
                <div><Badge status={selected.status} /></div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Timestamp</div>
                <div style={{ fontWeight: 600 }}>{new Date(selected.timestamp).toLocaleString()}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Distance</div>
                <div style={{ fontWeight: 600 }}>{selected.distance} cm</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Duration</div>
                <div style={{ fontWeight: 600 }}>{selected.parking_duration || '0'} seconds</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Zone</div>
                <div style={{ fontWeight: 600 }}>{selected.zone || 'Not specified'}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Vehicle Detected</div>
                <div style={{ fontWeight: 600 }}>{selected.vehicle_detected || 'NO'}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#888' }}>Signal Strength (RSSI)</div>
                <div style={{ fontWeight: 600 }}>{selected.rssi || '-'}</div>
              </div>
              {selected.sensor_types && (
                <div>
                  <div style={{ fontSize: 12, color: '#888' }}>Sensor Types</div>
                  <div style={{ fontWeight: 600 }}>{Array.isArray(selected.sensor_types) ? selected.sensor_types.join(', ') : selected.sensor_types}</div>
                </div>
              )}
              {selected.hall_value && (
                <div>
                  <div style={{ fontSize: 12, color: '#888' }}>Hall Sensor Value</div>
                  <div style={{ fontWeight: 600 }}>{selected.hall_value}</div>
                </div>
              )}
              {selected.sensor_calibrated !== undefined && (
                <div>
                  <div style={{ fontSize: 12, color: '#888' }}>Calibration Status</div>
                  <div style={{ fontWeight: 600, color: selected.sensor_calibrated ? '#10b981' : '#ef4444' }}>
                    {selected.sensor_calibrated ? '✓ Calibrated' : '✗ Not Calibrated'}
                  </div>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 8, padding: '8px 20px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setSelected(null)}>Close</button>
              <button style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 20px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setSelected(null)}>Mark as Reviewed</button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ marginTop: 48, textAlign: 'center', color: '#888', fontSize: 15 }}>
        Parking Management System v1.0 &nbsp;|&nbsp; System Status: <span style={{ color: '#10b981', fontWeight: 700 }}>Active</span> &nbsp;|&nbsp; Last Updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  );
};
export default ParkingDetails;