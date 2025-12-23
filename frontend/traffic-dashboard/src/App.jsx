import React from 'react';
import Header from './components/Header';
import StatsBar from './components/StatsBar';
import MapSection from './components/MapSection';
import Analytics from './components/Analytics';
import Overview from './components/Overview';

function App() {
  return (
    <div className="dashboard-container">
      <Header />
      <StatsBar />
      <MapSection />
      <Analytics />
      <Overview />
      {/* Footer mimic */}
      <footer style={{ backgroundColor: '#1a237e', height: '50px' }}></footer>
    </div>
  );
}

export default App;
