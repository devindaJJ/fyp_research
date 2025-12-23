import React, { useState } from 'react';
import './StatsBar.css';
import { Bell } from 'lucide-react';

const StatsBar = ({ activeTab, onTabChange }) => {
    const tabs = [
        'Home',
        'Traffic Monitoring',
        'Violation Detection',
        'Smart Parking',
        'Emergency Response'
    ];

    const [notificationCount] = useState(3);

    return (
        <div className="stats-bar">
            {tabs.map((label) => (
                <div
                    key={label}
                    className={`stat-item ${activeTab === label ? 'active' : ''}`}
                    onClick={() => onTabChange(label)}
                >
                    {label}
                </div>
            ))}

            {/* Notification Icon placed next to Emergency Response (the last item) */}
            <div className="stats-notification-container">
                <div
                    className="notification-bell"
                    onClick={() => onTabChange('Notifications')}
                    title="View All Notifications"
                >
                    <Bell size={20} color="#161e54" />
                    {notificationCount > 0 && <span className="stats-badge">{notificationCount}</span>}

                    <div className="notification-popup">
                        <div className="popup-header">Recent Alerts (Click to View All)</div>
                        <div className="popup-item">🚨 Speeding detected on Galle Rd</div>
                        <div className="popup-item">⚠️ Traffic congestion at Maradana</div>
                        <div className="popup-item">📸 New violation pending review</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StatsBar;
