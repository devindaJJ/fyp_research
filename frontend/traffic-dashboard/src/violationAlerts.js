import React from 'react';

const ViolationAlerts = ({ violations }) => {
  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'HIGH': return 'high-priority';
      case 'MEDIUM': return 'medium-priority';
      default: return 'low-priority';
    }
  };

  return (
    <div className="violation-alerts">
      <div className="section-header">
        <h2>🚨 Live Violation Alerts</h2>
        <span className="badge">{violations.length} Active</span>
      </div>

      {violations.length === 0 ? (
        <div className="no-violations">
          <p>🎉 No active violations detected</p>
        </div>
      ) : (
        <div className="violations-list">
          {violations.map((violation, index) => (
            <div key={index} className={`violation-card ${getPriorityColor(violation.priority)}`}>
              <div className="violation-header">
                <span className="priority-badge">{violation.priority} PRIORITY</span>
                <span className="violation-time">
                  {new Date(violation.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              <div className="violation-content">
                <p><strong>Illegal Parking Detected</strong></p>
                <p>📍 Location: {violation.location}</p>
                <p>🆔 Spot: {violation.spot_id}</p>
                <p>📏 Distance: {violation.distance}cm</p>
              </div>

              <div className="violation-actions">
                <button className="btn btn-dispatch">Dispatch Unit</button>
                <button className="btn btn-ignore">Mark as Resolved</button>
                <button className="btn btn-view">View Details</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ViolationAlerts;