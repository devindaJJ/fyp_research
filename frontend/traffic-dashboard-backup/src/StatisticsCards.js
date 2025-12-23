import React from 'react';

const StatisticsCards = ({ statistics, violations }) => {
  const stats = {
    totalSpots: statistics.total_records || 0,
    availableSpots: statistics.available_spots || 0,
    occupiedSpots: statistics.occupied_spots || 0,
    violationCount: statistics.violation_count || violations.length,
    utilizationRate: statistics.utilization_rate || 0
  };

  return (
    <div className="statistics-cards">
      <div className="stat-card available">
        <div className="stat-icon">🅿️</div>
        <div className="stat-info">
          <h3>Available Spots</h3>
          <div className="stat-value">{stats.availableSpots}</div>
        </div>
      </div>

      <div className="stat-card occupied">
        <div className="stat-icon">🚗</div>
        <div className="stat-info">
          <h3>Occupied Spots</h3>
          <div className="stat-value">{stats.occupiedSpots}</div>
        </div>
      </div>

      <div className="stat-card violations">
        <div className="stat-icon">🚨</div>
        <div className="stat-info">
          <h3>Active Violations</h3>
          <div className="stat-value">{stats.violationCount}</div>
        </div>
      </div>

      <div className="stat-card utilization">
        <div className="stat-icon">📈</div>
        <div className="stat-info">
          <h3>Utilization Rate</h3>
          <div className="stat-value">{stats.utilizationRate}%</div>
        </div>
      </div>
    </div>
  );
};

export default StatisticsCards;