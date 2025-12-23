import React from 'react';
import './StatsBar.css';

const StatsBar = ({ activeTab, onTabChange }) => {
    const tabs = [
        'Home',
        'Traffic Monitoring',
        'Violation Detection',
        'Smart Parking',
        'Emergency Response',
        'Reports',
        'History'
    ];

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
        </div>
    );
};

export default StatsBar;
