import { useState, useEffect } from 'react'
import './ViolationDetection.css'

const API_BASE_URL = 'http://localhost:8000/api'

export default function ViolationDetection() {
  const [allViolations, setAllViolations] = useState([])
  const [filteredViolations, setFilteredViolations] = useState([])
  const [liveViolations, setLiveViolations] = useState([])
  const [laneViolations, setLaneViolations] = useState([])
  const [safetyAlerts, setSafetyAlerts] = useState([])
  const [stats, setStats] = useState({
    total: 0,
    speeding: 0,
    lane: 0,
    dangerous: 0,
    today: 0
  })
  const [isMonitoring, setIsMonitoring] = useState(false)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [videoPath, setVideoPath] = useState('')

  // Check detection status on mount
  useEffect(() => {
    checkDetectionStatus()
    const interval = setInterval(checkDetectionStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  // Fetch live data when monitoring
  useEffect(() => {
    if (!isMonitoring) return
    fetchLiveData()
    const interval = setInterval(fetchLiveData, 2000)
    return () => clearInterval(interval)
  }, [isMonitoring])

  // Filter violations when search or filter changes
  useEffect(() => {
    let filtered = allViolations

    if (searchQuery) {
      filtered = filtered.filter(v => 
        (v.plate?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (v.plate_number?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (v.location?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (v.violation_type?.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (v.track_id?.toString().includes(searchQuery)) ||
        (v.vehicle_id?.toString().includes(searchQuery))
      )
    }

    if (filterType !== 'all') {
      filtered = filtered.filter(v => v.type === filterType)
    }

    setFilteredViolations(filtered)
  }, [searchQuery, filterType, allViolations])

  const checkDetectionStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/detection/status`)
      const data = await res.json()
      if (data.success) {
        setIsMonitoring(data.is_processing)
      }
      setLoading(false)
    } catch (err) {
      console.error('Error checking status:', err)
      setLoading(false)
    }
  }

  const fetchLiveData = async () => {
    try {
      const [violationsRes, laneViolationsRes, alertsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/detection/violations`),
        fetch(`${API_BASE_URL}/violations/lane`),
        fetch(`${API_BASE_URL}/detection/safety-alerts`),
        fetch(`${API_BASE_URL}/detection/stats`)
      ])

      const violationsData = await violationsRes.json()
      const laneViolationsData = await laneViolationsRes.json()
      const alertsData = await alertsRes.json()
      const statsData = await statsRes.json()

      if (violationsData.success) {
        const violations = violationsData.violations.map(v => ({
          ...v,
          type: 'speeding',
          timestamp: new Date().toISOString()
        }))
        setLiveViolations(violations)
        setAllViolations(prev => [...violations, ...prev].slice(0, 100))
      }

      if (laneViolationsData.success) {
        const laneVios = laneViolationsData.violations.map(v => ({
          ...v,
          type: 'lane',
          timestamp: v.timestamp || new Date().toISOString()
        }))
        setLaneViolations(laneVios)
        setAllViolations(prev => [...laneVios, ...prev].slice(0, 100))
      }

      if (alertsData.success) {
        setSafetyAlerts(alertsData.alerts?.slice(-10) || [])
      }

      if (statsData.success) {
        setStats({
          total: allViolations.length,
          speeding: statsData.stats?.speeding_violations || 0,
          lane: laneViolations.length,
          dangerous: statsData.stats?.safety_alerts?.total || 0,
          today: allViolations.filter(v =>
            new Date(v.timestamp).toDateString() === new Date().toDateString()
          ).length
        })
      }
    } catch (err) {
      console.error('Error fetching live data:', err)
    }
  }

  const startDetection = async () => {
    if (!videoPath) {
      alert('Please enter a video path')
      return
    }

    try {
      const res = await fetch(`${API_BASE_URL}/detection/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_path: videoPath })
      })
      const data = await res.json()
      if (data.success) {
        setIsMonitoring(true)
        setAllViolations([])
        setLiveViolations([])
        setSafetyAlerts([])
      } else {
        alert('Failed to start detection: ' + (data.error || 'Unknown error'))
      }
    } catch (err) {
      alert('Error starting detection: ' + err.message)
    }
  }

  const stopDetection = async () => {
    try {
      await fetch(`${API_BASE_URL}/detection/stop`, { method: 'POST' })
      setIsMonitoring(false)
    } catch (err) {
      console.error('Error stopping detection:', err)
    }
  }

  const exportViolations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/detection/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format: 'csv' })
      })
      const data = await res.json()
      if (data.success) {
        alert(`Exported to: ${data.export_path}`)
      }
    } catch (err) {
      alert('Export failed: ' + err.message)
    }
  }

  const formatTime = (timestamp) => new Date(timestamp).toLocaleTimeString()
  const formatDate = (timestamp) => new Date(timestamp).toLocaleDateString()

  if (loading) {
    return <div className="detection-dashboard loading">Loading...</div>
  }

  return (
    <div className="detection-dashboard">
      <header className="dashboard-header">
        <h1>Traffic Violation Detection</h1>
        <div className="status-badge">
          {isMonitoring ? (
            <span className="badge active">🔴 LIVE</span>
          ) : (
            <span className="badge inactive">⚪ OFFLINE</span>
          )}
        </div>
      </header>

      {/* Control Panel */}
      <div className="control-panel">
        <h3>🎥 Detection Control</h3>
        <div className="control-row">
          <input
            type="text"
            placeholder="Enter video path (e.g., videos/traffic.mp4)"
            value={videoPath}
            onChange={(e) => setVideoPath(e.target.value)}
            disabled={isMonitoring}
            className="video-input"
          />
          {!isMonitoring ? (
            <button onClick={startDetection} className="btn btn-start">
              ▶️ Start Detection
            </button>
          ) : (
            <button onClick={stopDetection} className="btn btn-stop">
              ⏹️ Stop Detection
            </button>
          )}
          <button onClick={exportViolations} className="btn btn-export" disabled={!isMonitoring}>
            💾 Export CSV
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Violations</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🚗</div>
          <div className="stat-number">{stats.speeding}</div>
          <div className="stat-label">Speeding Violations</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🛣️</div>
          <div className="stat-number">{stats.lane}</div>
          <div className="stat-label">Lane Violations</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-number">{stats.dangerous}</div>
          <div className="stat-label">Dangerous Driving</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📅</div>
          <div className="stat-number">{stats.today}</div>
          <div className="stat-label">Today's Violations</div>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="search-filter-bar">
        <input
          type="text"
          placeholder="🔍 Search by license plate or location..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="filter-select">
          <option value="all">All Violations</option>
          <option value="speeding">Speeding Only</option>
          <option value="lane">Lane Violations Only</option>
          <option value="dangerous">Dangerous Driving</option>
        </select>
      </div>

      {/* Live Violations Table */}
      {isMonitoring && liveViolations.length > 0 && (
        <div className="violations-section">
          <h2>🚨 Live Violations</h2>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Vehicle ID</th>
                  <th>License Plate</th>
                  <th>Speed</th>
                  <th>Limit</th>
                  <th>Excess</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {liveViolations.map((v) => (
                  <tr key={v.track_id} className="violation-row live">
                    <td>#{v.track_id}</td>
                    <td className="plate-number">{v.plate || 'Unknown'}</td>
                    <td className="speed-value">{v.speed?.toFixed(1)} km/h</td>
                    <td>{v.speed_limit} km/h</td>
                    <td className="excess-speed">+{(v.speed - v.speed_limit).toFixed(1)}</td>
                    <td>{formatTime(new Date())}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* All Violations Table */}
      <div className="violations-section">
        <h2>📋 Violation Records ({filteredViolations.length})</h2>
        {filteredViolations.length > 0 ? (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date & Time</th>
                  <th>Vehicle ID</th>
                  <th>License Plate</th>
                  <th>Type</th>
                  <th>Details</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredViolations.slice(0, 50).map((v, idx) => (
                  <tr key={idx} className="violation-row">
                    <td>{formatDate(v.timestamp)} {formatTime(v.timestamp)}</td>
                    <td>#{v.track_id || v.vehicle_id}</td>
                    <td className="plate-number">{v.plate || v.plate_number || 'Unknown'}</td>
                    <td>
                      {v.type === 'speeding' ? (
                        <span className="type-badge speeding">🚗 Speeding</span>
                      ) : v.type === 'lane' ? (
                        <span className="type-badge lane">🛣️ Lane Violation</span>
                      ) : (
                        <span className="type-badge dangerous">⚠️ Dangerous</span>
                      )}
                    </td>
                    <td>
                      {v.type === 'speeding' ? (
                        `${v.speed?.toFixed(1)} km/h (+${(v.speed - v.speed_limit).toFixed(1)} over limit)`
                      ) : v.type === 'lane' ? (
                        v.violation_type?.replace(/_/g, ' ').toUpperCase() || 'Lane Violation'
                      ) : (
                        v.description || 'Dangerous driving detected'
                      )}
                    </td>
                    <td>
                      <span className={`status-badge ${v.severity || 'medium'}`}>
                        {v.severity === 'high' ? '🔴 High' : v.severity === 'low' ? '🟡 Low' : '🟠 Medium'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="no-data">
            {searchQuery || filterType !== 'all' 
              ? 'No violations match your search criteria' 
              : 'No violations detected yet. Start detection to monitor traffic.'}
          </div>
        )}
      </div>

      {/* Safety Alerts */}
      {isMonitoring && safetyAlerts.length > 0 && (
        <div className="violations-section">
          <h2>⚡ Safety Alerts</h2>
          <div className="alerts-grid">
            {safetyAlerts.map((alert, idx) => (
              <div key={idx} className={`alert-card severity-${alert.severity?.toLowerCase()}`}>
                <div className="alert-header">
                  <span className="alert-type">{alert.type?.replace(/_/g, ' ').toUpperCase()}</span>
                  <span className="alert-time">{formatTime(alert.timestamp)}</span>
                </div>
                <div className="alert-body">{alert.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}