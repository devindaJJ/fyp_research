import React from 'react';
import StatisticsCards from './StatisticsCards';
import ParkingChart from './ParkingChart';
import RecentActivity from './RecentActivity';

const Dashboard = ({ parkingData, statistics, violations }) => {
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Real-time Parking Overview</h2>
        <p>Last updated: {new Date().toLocaleTimeString()}</p>
      </div>

      {/* Statistics Cards */}
      <StatisticsCards statistics={statistics} violations={violations} />

      <div className="dashboard-grid">
        {/* Charts Section */}
        <div className="chart-section">
          <ParkingChart parkingData={parkingData} />
        </div>

        {/* Recent Activity */}
        <div className="activity-section">
          <RecentActivity parkingData={parkingData} violations={violations} />
        </div>
      </div>
    </div>
  );
};

export default Dashboard;