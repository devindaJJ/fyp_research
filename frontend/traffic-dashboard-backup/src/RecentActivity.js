import React from 'react';

const RecentActivity = ({ parkingData, violations }) => {
  // Combine and sort parking events and violations by timestamp
  const activities = [];

  // Add parking events
  parkingData.slice(0, 10).forEach(record => {
    activities.push({
      type: 'parking',
      timestamp: record.timestamp,
      spotId: record.parking_spot_id || record.spot_id,
      status: record.status,
      message: `Spot ${record.parking_spot_id || record.spot_id} is now ${record.status}`
    });
  });

  // Add violation events
  violations.slice(0, 10).forEach(violation => {
    activities.push({
      type: 'violation',
      timestamp: violation.timestamp,
      spotId: violation.parking_spot_id || violation.spot_id,
      violationType: violation.violation_type,
      message: `${violation.violation_type} at Spot ${violation.parking_spot_id || violation.spot_id}`
    });
  });

  // Sort by timestamp (most recent first)
  activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  // Take only the most recent 15 activities
  const recentActivities = activities.slice(0, 15);

  const getActivityIcon = (activity) => {
    if (activity.type === 'violation') {
      return '🚨';
    }
    return activity.status === 'occupied' ? '🚗' : '🅿️';
  };

  const getActivityClass = (activity) => {
    if (activity.type === 'violation') {
      return 'violation';
    }
    return activity.status === 'occupied' ? 'occupied' : 'available';
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} hours ago`;
    return date.toLocaleString();
  };

  return (
    <div className="recent-activity">
      <h3>Recent Activity</h3>
      <div className="activity-list">
        {recentActivities.length > 0 ? (
          recentActivities.map((activity, index) => (
            <div key={index} className={`activity-item ${getActivityClass(activity)}`}>
              <div className="activity-icon">{getActivityIcon(activity)}</div>
              <div className="activity-content">
                <p className="activity-message">{activity.message}</p>
                <span className="activity-time">{formatTimestamp(activity.timestamp)}</span>
              </div>
            </div>
          ))
        ) : (
          <div className="no-activity">
            <p>No recent activity</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RecentActivity;
