import React, { useState } from 'react';
import Header from './components/Header';
import StatsBar from './components/StatsBar';
import MapSection from './components/MapSection';
import Analytics from './components/Analytics';
import Overview from './components/Overview';

function App() {
  const [activeTab, setActiveTab] = useState('Home');

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

      {activeTab !== 'Home' && (
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
