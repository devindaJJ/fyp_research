import React from 'react';
import './StatsBar.css';

const StatsBar = ({ activeTab, onTabChange }) => {
    const stats = [
        'Home',
        'Traffic Monitoring',
        'Smart Parking',
        'Emergency Response',
        'Violation Detection',
    ];

    return (
        <div className="stats-bar">
            {stats.map((label) => (
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
