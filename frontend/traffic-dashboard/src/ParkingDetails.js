import React, { useState, useMemo, useEffect } from 'react';
import './App.css';

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

const ParkingDetails = ({ parkingData = [] }) => {
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
    <div className="parking-dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1><span className="header-icon">{Icons.Parking}</span> Parking Management System</h1>
          <p className="header-subtitle">Real-time monitoring and analytics</p>
        </div>
        <div className="header-actions">
          <button className="btn-icon" onClick={refreshData} title="Refresh">
            {Icons.Refresh}
          </button>
          <button className="btn-icon" onClick={exportCSV} title="Export Data">
            {Icons.Export}
          </button>
          <button className="btn-icon" onClick={() => setShowFilters(!showFilters)} title="Filters">
            {Icons.Filter}
          </button>
        </div>
      </header>

      {/* Stats Overview */}
      <div className="stats-overview">
        <StatCard 
          title="Total Records" 
          value={stats.total} 
          icon={Icons.Chart}
          color="#3b82f6"
        />
        <StatCard 
          title="Occupied" 
          value={stats.occupied} 
          change={stats.total > 0 ? Math.round((stats.occupied / stats.total) * 100) : 0}
          icon={Icons.Car}
          color="#ef4444"
        />
        <StatCard 
          title="Vacant" 
          value={stats.vacant} 
          change={stats.total > 0 ? Math.round((stats.vacant / stats.total) * 100) : 0}
          icon="🅿️"
          color="#10b981"
        />
        <StatCard 
          title="Avg Duration" 
          value={`${stats.avgDuration}s`} 
          icon={Icons.Clock}
          color="#f59e0b"
        />
      </div>

      {/* Controls Bar */}
      <div className="controls-bar">
        <div className="search-container">
          <span className="search-icon">{Icons.Search}</span>
          <input 
            className="search-input" 
            placeholder="Search by location, device ID, or zone..." 
            value={query} 
            onChange={(e) => { setQuery(e.target.value); setPage(0); }}
          />
        </div>
        
        <div className="view-controls">
          <button 
            className={`view-toggle ${view === 'cards' ? 'active' : ''}`}
            onClick={() => setView('cards')}
            title="Card View"
          >
            ▦
          </button>
          <button 
            className={`view-toggle ${view === 'grid' ? 'active' : ''}`}
            onClick={() => setView('grid')}
            title="Grid View"
          >
            ⏹
          </button>
          <button 
            className={`view-toggle ${view === 'table' ? 'active' : ''}`}
            onClick={() => setView('table')}
            title="Table View"
          >
            ☰
          </button>
          <div className="results-count">
            {filtered.length} records found
          </div>
        </div>
      </div>

      {/* Main Content with Sidebar */}
      <div className="dashboard-content">
        {showFilters && (
          <div className="sidebar">
            <FilterPanel 
              filters={filters}
              setFilters={setFilters}
              onApply={() => setPage(0)}
            />
          </div>
        )}

        <main className={`main-content ${showFilters ? 'with-sidebar' : ''}`}>
          {filtered.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🅿️</div>
              <h3>No parking data found</h3>
              <p>Try adjusting your search or filters</p>
              <button className="btn-secondary" onClick={() => { setQuery(''); setFilters({}); }}>
                Clear all filters
              </button>
            </div>
          ) : view === 'cards' ? (
            <div className="cards-view">
              {current.map((record, i) => (
                <ParkingCard 
                  key={i} 
                  data={record} 
                  onClick={setSelected}
                />
              ))}
            </div>
          ) : view === 'grid' ? (
            <div className="grid-view">
              {current.map((record, i) => (
                <div key={i} className="grid-item" onClick={() => setSelected(record)}>
                  <div className="grid-item-header">
                    <Badge status={record.status} size="small" />
                    <span className="grid-time">{new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div className="grid-location">{record.location}</div>
                  <div className="grid-distance">{record.distance} cm</div>
                  <div className="grid-duration">{record.parking_duration || '0'}s</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
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
                    <tr key={i} className={record.status?.toLowerCase() === 'occupied' ? 'row-occupied' : ''}>
                      <td>{new Date(record.timestamp).toLocaleString()}</td>
                      <td><strong>{record.location}</strong></td>
                      <td><code>{record.device_id || record.device}</code></td>
                      <td>{record.distance} cm</td>
                      <td>{record.parking_duration || '0'}s</td>
                      <td><Badge status={record.status} size="small" /></td>
                      <td>{record.zone || '-'}</td>
                      <td>
                        <button 
                          className="btn-link"
                          onClick={() => setSelected(record)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {filtered.length > 0 && (
            <div className="pagination">
              <div className="pagination-info">
                Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length} records
              </div>
              <div className="pagination-controls">
                <button 
                  className="pagination-btn" 
                  disabled={page <= 0}
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                >
                  Previous
                </button>
                <div className="page-numbers">
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
                      <button
                        key={pageNum}
                        className={`page-number ${page === pageNum ? 'active' : ''}`}
                        onClick={() => setPage(pageNum)}
                        disabled={pageNum >= pageCount}
                      >
                        {pageNum + 1}
                      </button>
                    );
                  })}
                  {pageCount > 5 && <span>...</span>}
                </div>
                <button 
                  className="pagination-btn" 
                  disabled={page >= pageCount - 1}
                  onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))}
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Record Details Modal */}
      {selected && (
        <div className="modal-overlay" onClick={() => setSelected(null)}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Parking Record Details</h3>
              <button className="modal-close" onClick={() => setSelected(null)}>
                {Icons.Close}
              </button>
            </div>
            
            <div className="modal-body">
              <div className="detail-grid">
                <div className="detail-item">
                  <label>Location</label>
                  <div className="detail-value">{selected.location}</div>
                </div>
                <div className="detail-item">
                  <label>Device ID</label>
                  <div className="detail-value">{selected.device_id || selected.device}</div>
                </div>
                <div className="detail-item">
                  <label>Status</label>
                  <div><Badge status={selected.status} /></div>
                </div>
                <div className="detail-item">
                  <label>Timestamp</label>
                  <div className="detail-value">{new Date(selected.timestamp).toLocaleString()}</div>
                </div>
                <div className="detail-item">
                  <label>Distance</label>
                  <div className="detail-value">{selected.distance} cm</div>
                </div>
                <div className="detail-item">
                  <label>Duration</label>
                  <div className="detail-value">{selected.parking_duration || '0'} seconds</div>
                </div>
                <div className="detail-item">
                  <label>Zone</label>
                  <div className="detail-value">{selected.zone || 'Not specified'}</div>
                </div>
                <div className="detail-item">
                  <label>Vehicle Detected</label>
                  <div className="detail-value">{selected.vehicle_detected || 'NO'}</div>
                </div>
                {selected.hall_value && (
                  <div className="detail-item">
                    <label>Hall Sensor Value</label>
                    <div className="detail-value">{selected.hall_value}</div>
                  </div>
                )}
              </div>
              
              <div className="modal-actions">
                <button className="btn-secondary" onClick={() => setSelected(null)}>
                  Close
                </button>
                <button className="btn-primary" onClick={() => {
                  // Implement action (e.g., mark as resolved)
                  setSelected(null);
                }}>
                  Mark as Reviewed
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="dashboard-footer">
        <div className="footer-content">
          <span>Parking Management System v1.0</span>
          <span className="footer-status">
            <span className="status-indicator active"></span>
            System Status: <strong>Active</strong>
          </span>
          <span>Last Updated: {new Date().toLocaleTimeString()}</span>
        </div>
      </footer>
    </div>
  );
};

export default ParkingDetails;