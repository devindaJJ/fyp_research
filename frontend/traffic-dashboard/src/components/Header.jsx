import React, { useState } from 'react';
import './Header.css';
import { Bell } from 'lucide-react';

const Header = () => {
    const [notifications] = useState(3); // Mock notification count

    return (
        <header className="header">
            <div className="header-content">
                <div>
                    <h1>Urban Traffic Management System</h1>
                    <p>Real-time traffic monitoring and analysis dashboard</p>
                </div>
                <div className="header-actions">
                    <div className="notification-bell">
                        <Bell color="white" size={24} />
                        {notifications > 0 && <span className="badge">{notifications}</span>}
                        <div className="notification-popup">
                            <div className="popup-header">Recent Alerts</div>
                            <div className="popup-item">🚨 Speeding detected on Galle Rd</div>
                            <div className="popup-item">⚠️ Traffic congestion at Maradana</div>
                            <div className="popup-item">📸 New violation pending review</div>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
