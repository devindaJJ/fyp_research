import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatsBar from './components/StatsBar';
import MapSection from './components/MapSection';
import Analytics from './components/Analytics';
import SplashScreen from './components/SplashScreen';
import ViolationDetection from './components/ViolationDetection';
import NotificationsView from './components/NotificationsView';
import SmartParking from './components/SmartParking';
import TrafficMonitoring from './components/TrafficMonitoring';
import TrafficAnalyzer from './TrafficAnalyzer.jsx';

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [activeTab, setActiveTab] = useState('Home');

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 3800); // 3.8 seconds
    return () => clearTimeout(timer);
  }, []);

  if (showSplash) {
    return <SplashScreen />;
  }

  return (
    <div className="app-container">
      <Header />
      <StatsBar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="main-content">
        {activeTab === 'Home' && (
          <>
            <div className="dashboard-grid">
              <MapSection />
              <Analytics />
            </div>
          </>
        )}

        {activeTab === 'Violation Detection' && <ViolationDetection />}

        {activeTab === 'Smart Parking' && <SmartParking />}

        {activeTab === 'Notifications' && <NotificationsView />}

        {activeTab === 'Traffic Monitoring' && <TrafficAnalyzer />}

        {/* Placeholders for other tabs */}
        {activeTab === 'Emergency Response' && (
          <div className="placeholder-section">
            <h2>{activeTab}</h2>
            <p>Module under development.</p>
          </div>
        )}
      </main>
      <footer style={{ backgroundColor: '#1a237e', height: '50px' }}></footer>
    </div>
  );
}

export default App;
