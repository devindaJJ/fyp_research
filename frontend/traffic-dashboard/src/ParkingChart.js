import React from 'react';

const ParkingChart = ({ parkingData }) => {
  // Get the latest parking status for each spot
  const parkingSpots = parkingData.reduce((acc, record) => {
    const spotId = record.parking_spot_id || record.spot_id;
    if (spotId && (!acc[spotId] || new Date(record.timestamp) > new Date(acc[spotId].timestamp))) {
      acc[spotId] = record;
    }
    return acc;
  }, {});

  const spots = Object.values(parkingSpots);
  const availableCount = spots.filter(spot => spot.status === 'available').length;
  const occupiedCount = spots.filter(spot => spot.status === 'occupied').length;
  const total = spots.length || 1;

  const availablePercentage = (availableCount / total) * 100;
  const occupiedPercentage = (occupiedCount / total) * 100;

  return (
    <div className="parking-chart">
      <h3>Parking Occupancy</h3>
      
      {/* Bar Chart */}
      <div className="chart-container">
        <div className="bar-chart">
          <div className="bar-row">
            <div className="bar-label">Available</div>
            <div className="bar-wrapper">
              <div 
                className="bar available-bar" 
                style={{ width: `${availablePercentage}%` }}
              >
                <span className="bar-value">{availableCount}</span>
              </div>
            </div>
          </div>
          <div className="bar-row">
            <div className="bar-label">Occupied</div>
            <div className="bar-wrapper">
              <div 
                className="bar occupied-bar" 
                style={{ width: `${occupiedPercentage}%` }}
              >
                <span className="bar-value">{occupiedCount}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Parking Grid Visualization */}
      <div className="parking-grid-viz">
        <h4>Parking Spots Status</h4>
        <div className="spots-grid">
          {spots.length > 0 ? (
            spots.map((spot, index) => (
              <div 
                key={index}
                className={`parking-spot ${spot.status}`}
                title={`Spot ${spot.parking_spot_id || spot.spot_id}: ${spot.status}`}
              >
                <span className="spot-number">{spot.parking_spot_id || spot.spot_id}</span>
                <span className="spot-icon">
                  {spot.status === 'occupied' ? '🚗' : '🅿️'}
                </span>
              </div>
            ))
          ) : (
            <p className="no-data">No parking data available</p>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="chart-legend">
        <div className="legend-item">
          <div className="legend-color available"></div>
          <span>Available</span>
        </div>
        <div className="legend-item">
          <div className="legend-color occupied"></div>
          <span>Occupied</span>
        </div>
      </div>
    </div>
  );
};

export default ParkingChart;
