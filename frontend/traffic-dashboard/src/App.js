import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Dashboard from './Dashboard';
import ViolationAlerts from './violationAlerts';
import SystemHealth from './SystemHealth';
import ParkingDetails from './ParkingDetails';
import Analytics from './Analytics';
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

      if (parkingRes.data.success) {
        // Normalize status and field names for UI
        const normalized = parkingRes.data.data.map(r => ({
          ...r,
          status: (r.status || r.Status || '').toString().toLowerCase(),
          timestamp: r.timestamp || r.Time || r.time,
          parking_spot_id: r.spot_id || r.parking_spot_id || r.spotId || null
        }));
        setParkingData(normalized);
      }
      if (violationsRes.data.success) setViolations(violationsRes.data.violations);
      if (statsRes.data.success) setStatistics(statsRes.data.statistics);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setLoading(false);
    }
  };

  const generateRecord = (location) => {
    const now = new Date().toISOString().replace('T', ' ').slice(0, 19);
    const distance = Math.round((Math.random() * 290 + 5) * 100) / 100;
    const status = distance < 200 ? 'OCCUPIED' : 'VACANT';
    return {
      timestamp: now,
      device: `ESP32_${Math.ceil(Math.random()*10)}`,
      location: location || 'Colombo_Parking_01',
      distance: distance,
      vehicle_detected: distance < 200 ? 'YES' : 'NO',
      parking_duration: distance < 200 ? Math.floor(Math.random()*3600) : 0,
      rssi: `${-30 - Math.floor(Math.random()*60)} dBm`,
      lat: 6.927 + (Math.random()-0.5)*0.02,
      lon: 79.861 + (Math.random()-0.5)*0.02,
      Status: status
    };
  };

  const simulateAndIngest = async (count = 50) => {
    try {
      const records = Array.from({length: count}).map(()=> generateRecord());
      await axios.post(`${API_BASE}/ingest-parking`, records);
      // refetch after ingest
      await fetchData();
    } catch (err) {
      console.error('Simulation error', err);
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
        <div className="header-actions">
          <button className="btn-sim" onClick={()=> simulateAndIngest(50)}>Simulate 50</button>
        </div>
        <nav className="nav-tabs">
          <button
            className={activeTab === 'dashboard' ? 'active' : ''}
            onClick={() => setActiveTab('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={activeTab === 'accidents' ? 'active' : ''}
            onClick={() => setActiveTab('accidents')}
          >
            🚑 Accident Detection
          </button>
          <button
            className={activeTab === 'violations' ? 'active' : ''}
            onClick={() => setActiveTab('violations')}
          >
              Violations
          </button>
          <button
            className={activeTab === 'map' ? 'active' : ''}
            onClick={() => setActiveTab('map')}
          >
            🗺️ Parking Map
          </button>
          
          <button 
            className={activeTab === 'analytics' ? 'active' : ''}
            onClick={() => setActiveTab('analytics')}
          >
            📈 Analytics
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
        {activeTab === 'accidents' && (
          <AccidentDetection />
        )}
        {activeTab === 'violations' && (
          <ViolationAlerts violations={violations} />
        )}
        {activeTab === 'map' && (
          <ParkingDetails parkingData={parkingData} />
        )}
        
        {activeTab === 'analytics' && (
          <Analytics parkingData={parkingData} />
        )}
        {activeTab === 'health' && (
          <SystemHealth />
        )}
      </main>
    </div>
  );
}

export default App;
