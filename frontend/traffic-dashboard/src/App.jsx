import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import StatsBar from './components/StatsBar';
import MapSection from './components/MapSection';
import Analytics from './components/Analytics';
import Overview from './components/Overview';
import SplashScreen from './components/SplashScreen';
import ViolationDetection from './components/ViolationDetection';

function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [activeTab, setActiveTab] = useState('Home');

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 3800); // 3.5s delay + 0.3s fade out buffer
    return () => clearTimeout(timer);
  }, []);

  if (showSplash) {
    return <SplashScreen />;
  }

  return (
    <div className="dashboard-container">
      <Header />
      <StatsBar activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'Home' && (
        <>
          <MapSection />
          <Analytics />
          <Overview />
        </>
      )}

      {activeTab === 'Violation Detection' && <ViolationDetection />}

      {activeTab !== 'Home' && activeTab !== 'Violation Detection' && (
        <div className="section" style={{ textAlign: 'center', padding: '4rem' }}>
          <h2>{activeTab} Module</h2>
          <p>This module is currently under development.</p>
        </div>
      )}

      {/* Footer mimic */}
      <footer style={{ backgroundColor: '#1a237e', height: '50px' }}></footer>
    </div>
  );
}

export default App;
