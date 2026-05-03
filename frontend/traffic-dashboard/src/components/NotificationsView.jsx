import React, { useState } from 'react';
import './NotificationsView.css';
import { Bell, AlertTriangle, Info, CheckCircle } from 'lucide-react';

const INITIAL_NOTIFICATIONS = [
    { id: 1, type: 'alert', title: 'Speeding Detected', message: 'Vehicle WP CAM-1234 exceeded limit on Galle Rd.', time: '2 mins ago', read: false },
    { id: 2, type: 'warning', title: 'Congestion Alert', message: 'Heavy traffic detected at Maradana Junction.', time: '15 mins ago', read: false },
    { id: 3, type: 'info', title: 'New Evidence Uploaded', message: 'Evidence pending review for Violation #V004.', time: '1 hour ago', read: true },
    { id: 4, type: 'success', title: 'System Update', message: 'Camera #4 firmware updated successfully.', time: '2 hours ago', read: true },
    { id: 5, type: 'alert', title: 'Lane Violation', message: 'Bus detected in car-only lane at Pettah.', time: 'Yesterday', read: true },
];

const NotificationsView = () => {
    const [notifications, setNotifications] = useState(INITIAL_NOTIFICATIONS);

    const markAsRead = (id) => {
        setNotifications(prev => prev.map(notif =>
            notif.id === id ? { ...notif, read: true } : notif
        ));
    };

    const getIcon = (type) => {
        switch (type) {
            case 'alert': return <Bell size={20} color="#e74c3c" />;
            case 'warning': return <AlertTriangle size={20} color="#f39c12" />;
            case 'success': return <CheckCircle size={20} color="#2ecc71" />;
            case 'info': default: return <Info size={20} color="#3498db" />;
        }
    };

    return (
        <div className="notifications-page section">
            <div className="section-header-row">
                <h2 className="section-title">All Notifications</h2>
            </div>

            <div className="notifications-container">
                {notifications.map((item) => (
                    <div
                        key={item.id}
                        className={`notification-card ${item.read ? 'read' : 'unread'}`}
                        onClick={() => markAsRead(item.id)}
                    >
                        <div className="notif-icon-wrapper">
                            {getIcon(item.type)}
                        </div>
                        <div className="notif-content">
                            <div className="notif-header">
                                <h4>{item.title}</h4>
                                <span className="notif-time">{item.time}</span>
                            </div>
                            <p>{item.message}</p>
                        </div>
                        {!item.read && <div className="unread-dot"></div>}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default NotificationsView;
