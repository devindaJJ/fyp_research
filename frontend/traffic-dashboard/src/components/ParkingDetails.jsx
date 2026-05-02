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
  Check: '✓'
};

const PAGE_SIZE = 12;

function Badge({ status, size = 'medium' }) {
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
  
  return (
    <div 
      className={`parking-card ${isRecent ? 'recent' : ''} ${data.status?.toLowerCase() === 'occupied' ? 'occupied' : ''}`}
      onClick={() => onClick(data)}
    >
      <div className="parking-card-header">
        <div className="parking-card-location">
          <span className="location-icon">{Icons.Location}</span>
          <div>
            <h4>{data.location || 'Unknown Location'}</h4>
            <p className="spot-id">{data.parking_spot_id || data.device_id || 'N/A'}</p>
          </div>
        </div>
        <Badge status={data.status} />
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
  
  return (
    <div className="filter-panel">
      <div className="filter-header">
        <h4>{Icons.Filter} Filters</h4>
      </div>
      
      <div className="filter-group">
        <label>Status</label>
        <select 
          value={localFilters.status}
          onChange={(e) => setLocalFilters({...localFilters, status: e.target.value})}
        >
          {statusOptions.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label>Zone</label>
        <select 
          value={localFilters.zone}
          onChange={(e) => setLocalFilters({...localFilters, zone: e.target.value})}
        >
          {zoneOptions.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
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
      
      <div className="filter-group">
        <label>Time Range</label>
        <select 
          value={localFilters.timeRange}
          onChange={(e) => setLocalFilters({...localFilters, timeRange: e.target.value})}
        >
          <option value="">All Time</option>
          <option value="1h">Last Hour</option>
          <option value="6h">Last 6 Hours</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
        </select>
      </div>
      
      <div className="filter-actions">
        <button className="btn-secondary" onClick={() => setLocalFilters({ status: '', zone: '', distanceMin: '', distanceMax: '', timeRange: '' })}>
          Clear All
        </button>
        <button className="btn-primary" onClick={() => { setFilters(localFilters); onApply(); }}>
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
  const [filters, setFilters] = useState({
    status: '',
    zone: '',
    distanceMin: '',
    distanceMax: '',
    timeRange: ''
  });
  const [stats, setStats] = useState({ total: 0, occupied: 0, vacant: 0, avgDuration: 0 });

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
    setStats({
      total: validData.length,
      occupied: occupied.length,
      vacant: validData.length - occupied.length,
      avgDuration
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
    
    // Apply filters
    if (filters.status) {
      list = list.filter(r => r.status?.toLowerCase().includes(filters.status.toLowerCase()));
    }
    
    if (filters.zone) {
      list = list.filter(r => r.zone === filters.zone);
    }
    
    if (filters.distanceMin) {
      const min = parseFloat(filters.distanceMin);
      list = list.filter(r => parseFloat(r.distance) >= min);
    }
    
    if (filters.distanceMax) {
      const max = parseFloat(filters.distanceMax);
      list = list.filter(r => parseFloat(r.distance) <= max);
    }
    
    if (filters.timeRange) {
      const now = new Date();
      const cutoff = new Date(now);
      
      switch(filters.timeRange) {
        case '1h': cutoff.setHours(now.getHours() - 1); break;
        case '6h': cutoff.setHours(now.getHours() - 6); break;
        case '24h': cutoff.setDate(now.getDate() - 1); break;
        case '7d': cutoff.setDate(now.getDate() - 7); break;
      }
      
      list = list.filter(r => new Date(r.timestamp) >= cutoff);
    }
    
    // Sort newest first
    list.sort((a,b) => new Date(b.timestamp || 0) - new Date(a.timestamp || 0));
    return list;
  }, [parkingData, query, filters]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const exportCSV = () => {
    const rows = filtered.map(r => ([
      r.timestamp || '',
      r.device_id || r.device || '',
      r.location || '',
      r.distance || '',
      r.vehicle_detected || '',
      r.parking_duration || '',
      r.zone || '',
      r.status || '',
      r.latitude || r.lat || '',
      r.longitude || r.lon || ''
    ]));
    const header = ['Timestamp','Device ID','Location','Distance (cm)','Vehicle Detected','Duration (s)','Zone','Status','Latitude','Longitude'];
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
        <span style={{ fontSize: '12px' }}>▲</span> 52%
      </div>
    </div>
    <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
      {Math.round((26 / 50) * 100)}% of total
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
        <span style={{ fontSize: '12px' }}>▲</span> 48%
      </div>
    </div>
    <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
      Available for parking
    </div>
  </div>

  {/* Avg Duration Card */}
  <div style={{
    background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    borderRadius: '16px',
    padding: '24px',
    color: 'white',
    boxShadow: '0 4px 20px rgba(245, 158, 11, 0.3)',
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
      ⏱️
    </div>
    <div style={{ fontSize: '14px', opacity: 0.9, marginBottom: '8px' }}>
      Avg Duration
    </div>
    <div style={{ 
      fontSize: '36px', 
      fontWeight: '700',
      marginBottom: '4px',
      display: 'flex',
      alignItems: 'baseline'
    }}>
        {stats.avgDuration}
      <div style={{
        fontSize: '14px',
        marginLeft: '8px',
        padding: '2px 8px',
        background: 'rgba(255, 255, 255, 0.2)',
        borderRadius: '12px',
        fontWeight: '600',
        color: '#ffd700'
      }}>
        No data
      </div>
    </div>
    <div style={{ fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
      No parking activity recorded
    </div>
  </div>
</div>

      {/* Search and View Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px #0001', padding: '6px 14px' }}>
          <span style={{ fontSize: 18, color: '#3b82f6' }}>{Icons.Search}</span>
          <input style={{ border: 'none', outline: 'none', fontSize: 15, background: 'transparent', minWidth: 220 }} placeholder="Search by location, device ID, or zone..." value={query} onChange={e => { setQuery(e.target.value); setPage(0); }} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button style={{ background: view === 'cards' ? '#3b82f6' : '#fff', color: view === 'cards' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('cards')}>Cards</button>
          <button style={{ background: view === 'grid' ? '#3b82f6' : '#fff', color: view === 'grid' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('grid')}>Grid</button>
          <button style={{ background: view === 'table' ? '#3b82f6' : '#fff', color: view === 'table' ? '#fff' : '#222', border: '1px solid #e0e7ef', borderRadius: 6, padding: '6px 14px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setView('table')}>Table</button>
          <span style={{ fontSize: 14, color: '#555', marginLeft: 12 }}>{filtered.length} records found</span>
        </div>
      </div>

      {/* Main Content */}
      <div>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', marginTop: 60, color: '#888' }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>{Icons.Parking}</div>
            <h3 style={{ fontWeight: 700, fontSize: 22 }}>No parking data found</h3>
            <p style={{ color: '#888', marginBottom: 18 }}>Try adjusting your search or filters</p>
            <button style={{ background: '#fff', border: '1px solid #e0e7ef', borderRadius: 8, padding: '8px 20px', fontWeight: 600, cursor: 'pointer' }} onClick={() => { setQuery(''); setFilters({ status: '', zone: '', distanceMin: '', distanceMax: '', timeRange: '' }); }}>Clear all filters</button>
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
            {current.map((record, i) => (
              <div key={i} style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px #0001', padding: 14, minHeight: 80, display: 'flex', flexDirection: 'column', gap: 6, cursor: 'pointer' }} onClick={() => setSelected(record)}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Badge status={record.status} size="small" />
                  <span style={{ fontSize: 12, color: '#888' }}>{new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{record.location}</div>
                <div style={{ fontSize: 12, color: '#555' }}>Distance: {record.distance} cm</div>
                <div style={{ fontSize: 12, color: '#555' }}>Duration: {record.parking_duration || '0'}s</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px #0001', padding: 0, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 15 }}>
              <thead>
                <tr style={{ background: '#f4f6fa', color: '#222', fontWeight: 700 }}>
                  <th style={{ padding: '10px 8px' }}>Time</th>
                  <th>Location</th>
                  <th>Device ID</th>
                  <th>Distance</th>
                  <th>Duration</th>
                  <th>Status</th>
                  <th>Zone</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {current.map((record, i) => (
                  <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f4f6fa' }}>
                    <td style={{ padding: '8px 6px' }}>{new Date(record.timestamp).toLocaleString()}</td>
                    <td><strong>{record.location}</strong></td>
                    <td><code>{record.device_id || record.device}</code></td>
                    <td>{record.distance} cm</td>
                    <td>{record.parking_duration || '0'}s</td>
                    <td><Badge status={record.status} size="small" /></td>
                    <td>{record.zone || '-'}</td>
                    <td>
                      <button style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, padding: '4px 12px', fontWeight: 600, cursor: 'pointer' }} onClick={() => setSelected(record)}>
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
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
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: '#0008', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }} onClick={() => setSelected(null)}>
          <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 4px 24px #0003', padding: 32, minWidth: 340, maxWidth: 420, width: '100%', position: 'relative' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <h3 style={{ fontWeight: 800, fontSize: 22, margin: 0 }}>Parking Record Details</h3>
              <button style={{ background: 'none', border: 'none', fontSize: 22, color: '#888', cursor: 'pointer' }} onClick={() => setSelected(null)}>{Icons.Close}</button>
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
              {selected.hall_value && (
                <div>
                  <div style={{ fontSize: 12, color: '#888' }}>Hall Sensor Value</div>
                  <div style={{ fontWeight: 600 }}>{selected.hall_value}</div>
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