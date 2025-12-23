import React from 'react';
import './StatsBar.css';

const StatsBar = () => {
    const stats = [
        { label: 'Traffic Monitoring', active: true },
        { label: 'Smart Parking', active: false },
        { label: 'Emergency Response', active: false },
        { label: 'Violation Detection', active: false },
    ];

    return (
        <div className="stats-bar">
            {stats.map((stat, index) => (
                <div key={index} className={`stat-item ${stat.active ? 'active' : ''}`}>
                    {stat.label}
                </div>
            ))}
        </div>
    );
};

export default StatsBar;
