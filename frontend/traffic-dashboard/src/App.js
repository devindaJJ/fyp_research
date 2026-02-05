import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Dashboard from './Dashboard';
import ViolationAlerts from './violationAlerts';
import SystemHealth from './SystemHealth';
import ParkingMap from './Dashboard';
import TrafficAnalyzer from './TrafficAnalyzer';
import './App.css';

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [parkingData, setParkingData] = useState([]);
  const [violations, setViolations] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [parkingRes, violationsRes, statsRes] = await Promise.all([
        axios.get(`${API_BASE}/parking-data`),
        axios.get(`${API_BASE}/violations`),
        axios.get(`${API_BASE}/statistics`)
      ]);

      if (parkingRes.data.success) setParkingData(parkingRes.data.data);
      if (violationsRes.data.success) setViolations(violationsRes.data.violations);
      if (statsRes.data.success) setStatistics(statsRes.data.statistics);
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading Traffic Management System...</p>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="app-header">
        <h1>🚦 Urban Traffic Management System</h1>
        <nav className="nav-tabs">
          <button 
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button 
            className={activeTab === 'traffic' ? 'active' : ''}
            onClick={() => setActiveTab('traffic')}
          >
            🚗 Traffic Analyzer
          </button>
          <button 
            className={activeTab === 'violations' ? 'active' : ''}
            onClick={() => setActiveTab('violations')}
          >
            🚨 Violations
          </button>
          <button 
            className={activeTab === 'map' ? 'active' : ''}
            onClick={() => setActiveTab('map')}
          >
            🗺️ Parking Map
          </button>
          <button 
            className={activeTab === 'health' ? 'active' : ''}
            onClick={() => setActiveTab('health')}
          >
            ⚙️ System Health
          </button>
        </nav>
      </header>

      <main className="main-content">
        {activeTab === 'dashboard' && (
          <Dashboard 
            parkingData={parkingData} 
            statistics={statistics}
            violations={violations}
          />
        )}
        {activeTab === 'traffic' && (
          <TrafficAnalyzer />
        )}
        {activeTab === 'violations' && (
          <ViolationAlerts violations={violations} />
        )}
        {activeTab === 'map' && (
          <ParkingMap parkingData={parkingData} />
        )}
        {activeTab === 'health' && (
          <SystemHealth />
        )}
      </main>
    </div>
  );
}

export default App;