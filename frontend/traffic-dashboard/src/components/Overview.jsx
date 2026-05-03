import React from 'react';
import './Overview.css';

const Overview = () => {
    return (
        <div className="section overview-section">
            <h2 className="section-title">Overview</h2>
            <div className="overview-content">
                <p>
                    <strong>An Urban Traffic Management System (UTMS)</strong> is a system used to control and monitor traffic in cities. It helps reduce traffic congestion, accidents, and travel time by using smart technologies like cameras and sensors.
                </p>
                <p>
                    The system monitors traffic flow in real time, controls traffic signals, detects accidents, and provides alerts and route suggestions to drivers. It also helps traffic police and city authorities manage roads more efficiently.
                </p>
                <p>
                    Overall, an Urban Traffic Management System makes city traffic safer, faster, and more organized.
                </p>
            </div>
        </div>
    );
};

export default Overview;
