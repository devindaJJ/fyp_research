import React, { useState, useEffect } from 'react';
import axios from 'axios';

const SystemHealth = () => {
  const [healthData, setHealthData] = useState({
    apiStatus: 'checking',
    databaseStatus: 'checking',
    esp32Status: 'checking',
    lastUpdate: null,
    uptime: 0
  });

  useEffect(() => {
    fetchHealthData();
    const interval = setInterval(fetchHealthData, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchHealthData = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/health');
      if (response.data.success) {
        setHealthData({
          apiStatus: 'operational',
          databaseStatus: response.data.database_connected ? 'operational' : 'error',
          esp32Status: response.data.esp32_connected ? 'operational' : 'warning',
          lastUpdate: new Date().toLocaleString(),
          uptime: response.data.uptime || 0
        });
      }
    } catch (error) {
      console.error('Error fetching health data:', error);
      setHealthData(prev => ({
        ...prev,
        apiStatus: 'error',
        lastUpdate: new Date().toLocaleString()
      }));
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'operational':
        return '#2ecc71';
      case 'warning':
        return '#f39c12';
      case 'error':
        return '#e74c3c';
      default:
        return '#95a5a6';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'operational':
        return '✅';
      case 'warning':
        return '⚠️';
      case 'error':
        return '❌';
      default:
        return '⏳';
    }
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="system-health">
      <div className="health-header">
        <h2>⚙️ System Health Monitor</h2>
        <p>Last checked: {healthData.lastUpdate || 'Never'}</p>
      </div>

      <div className="health-grid">
        <div className="health-card" style={{ borderLeftColor: getStatusColor(healthData.apiStatus) }}>
          <div className="health-icon">{getStatusIcon(healthData.apiStatus)}</div>
          <div className="health-info">
            <h3>API Server</h3>
            <p className="health-status">{healthData.apiStatus}</p>
            <p className="health-detail">Backend API communication</p>
          </div>
        </div>

        <div className="health-card" style={{ borderLeftColor: getStatusColor(healthData.databaseStatus) }}>
          <div className="health-icon">{getStatusIcon(healthData.databaseStatus)}</div>
          <div className="health-info">
            <h3>Database</h3>
            <p className="health-status">{healthData.databaseStatus}</p>
            <p className="health-detail">Google Sheets connection</p>
          </div>
        </div>

        <div className="health-card" style={{ borderLeftColor: getStatusColor(healthData.esp32Status) }}>
          <div className="health-icon">{getStatusIcon(healthData.esp32Status)}</div>
          <div className="health-info">
            <h3>ESP32 Devices</h3>
            <p className="health-status">{healthData.esp32Status}</p>
            <p className="health-detail">Hardware sensors status</p>
          </div>
        </div>

        <div className="health-card" style={{ borderLeftColor: '#3498db' }}>
          <div className="health-icon">⏱️</div>
          <div className="health-info">
            <h3>System Uptime</h3>
            <p className="health-status">{formatUptime(healthData.uptime)}</p>
            <p className="health-detail">Time since last restart</p>
          </div>
        </div>
      </div>

      <div className="health-logs">
        <h3>System Information</h3>
        <div className="log-item">
          <span className="log-time">{new Date().toLocaleTimeString()}</span>
          <span className="log-message">System health check completed</span>
        </div>
        <div className="log-item">
          <span className="log-time">{new Date().toLocaleTimeString()}</span>
          <span className="log-message">All services monitored</span>
        </div>
      </div>
    </div>
  );
};

export default SystemHealth;
