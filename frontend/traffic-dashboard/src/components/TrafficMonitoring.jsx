import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { ChevronDown, MapPin, Clock, Calendar, Activity } from 'lucide-react';
import './TrafficMonitoring.css';
import TrafficMap from './TrafficMap';

const TrafficMonitoring = () => {
    const [currentTime, setCurrentTime] = useState(new Date());
    const [routes, setRoutes] = useState([]);

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    const formatDate = (date) => {
        return date.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' });
    };

    const formatTime = (date) => {
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    };


    useEffect(() => {
    setRoutes([
        {
            polyline: "a~l~Fjk~uOwHJy@P",
            is_primary: true
        }
    ]);
}, []);



    // Mock data for Congestion Analysis chart
    const chartData = [
        { time: '8:00', blue: 20, gray: 17, orange: 3 },
        { time: '8:15', blue: 14, gray: 11, orange: 2 },
        { time: '8:30', blue: 27, gray: 13, orange: 8 },
        { time: '8:45', blue: 19, gray: 21, orange: 0 },
    ];

    // Mock heatmap data for Colombo
    const heatmapPoints = [
        { position: [6.9271, 79.8612], intensity: 0.8, name: "Fort" },
        { position: [6.9016, 79.8552], intensity: 0.6, name: "Bambalapitiya" },
        { position: [6.9148, 79.8732], intensity: 0.9, name: "Maradana" },
        { position: [6.9213, 79.8511], intensity: 0.4, name: "Pettah" },
        { position: [6.8912, 79.8752], intensity: 0.7, name: "Havelock Town" },
    ];

    return (
        <div className="traffic-monitoring-container">
            {/* Header Controls */}
            <div className="tm-header">
                <div className="tm-control-group">
                    <div className="tm-dropdown">
                        <span>Location</span>
                        <ChevronDown size={18} />
                    </div>
                </div>

                <div className="tm-control-group">
                    <div className="tm-status-pill">
                        <span className="pill-label">Congestion Type</span>
                        <span className="pill-value">Normal</span>
                    </div>
                </div>

                <div className="tm-info-group">
                    <div className="tm-info-item">
                        <Calendar size={16} />
                        <span>{formatDate(currentTime)}</span>
                    </div>
                    <div className="tm-info-item time-pill">
                        <Clock size={16} />
                        <span>{formatTime(currentTime)}</span>
                    </div>
                </div>
            </div>

            <div className="tm-main-layout">
                <div className="tm-content-left">
                    {/* Live Congestion Heatmap */}
                    <div className="tm-section-card map-card">
                        <h3 className="tm-section-title">Live Congestion Heatmap</h3>
                        <div className="tm-map-wrapper">
                            <MapContainer center={[6.9271, 79.91]} zoom={12} style={{ height: '300px', width: '100%' }}>
                                <TileLayer
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                />
                                {heatmapPoints.map((point, idx) => (
                                    <CircleMarker
                                        key={idx}
                                        center={point.position}
                                        radius={20 * point.intensity}
                                        fillColor={point.intensity > 0.7 ? '#ff4d4d' : point.intensity > 0.4 ? '#ffa500' : '#ffff00'}
                                        color="transparent"
                                        fillOpacity={0.6}
                                    >
                                        <Popup>{point.name} Congestion</Popup>
                                    </CircleMarker>
                                ))}
                            </MapContainer>
                        </div>
                    </div>

                    {/* Congestion Analysis Chart */}
                    <div className="tm-section-card chart-card">
                        <h3 className="tm-section-title">Congestion Analysis</h3>
                        <div className="tm-chart-wrapper">
                            <ResponsiveContainer width="100%" height={250}>
                                <LineChart data={chartData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="time" axisLine={false} tickLine={false} />
                                    <YAxis axisLine={false} tickLine={false} />
                                    <Tooltip />
                                    <Line type="monotone" dataKey="blue" stroke="#2251cc" strokeWidth={3} dot={{ r: 4, fill: '#2251cc' }} />
                                    <Line type="monotone" dataKey="gray" stroke="#9e9e9e" strokeWidth={3} dot={{ r: 4, fill: '#9e9e9e' }} />
                                    <Line type="monotone" dataKey="orange" stroke="#ff9800" strokeWidth={3} dot={{ r: 4, fill: '#ff9800' }} />
                                    <text x="50%" y="100%" textAnchor="middle" fill="#757575" fontSize={12} dy={-10}>
                                        Time Interval
                                    </text>
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* Live Traffic Routes - Google Map */}
                <div className="tm-section-card map-card">
                   <h3 className="tm-section-title">Live Traffic Routes (Google Maps)</h3>
                    <div className="tm-map-wrapper">
                        <TrafficMap routes={routes} />
                    </div>
                </div>



                <div className="tm-sidebar">
                    <div className="tm-stat-card">
                        <h4>Total Vehicles</h4>
                        <div className="stat-value">1,248</div>
                        <div className="stat-trend positive">+12% vs last hour</div>
                    </div>

                    <div className="tm-stat-card">
                        <h4>Congested Roads</h4>
                        <div className="road-list">
                            <div className="road-item">
                                <span>Galle Road</span>
                                <span className="severity high">High</span>
                            </div>
                            <div className="road-item">
                                <span>Maradana Road</span>
                                <span className="severity medium">Medium</span>
                            </div>
                        </div>
                    </div>

                    <div className="tm-stat-card">
                        <h4>Average Speed</h4>
                        <div className="stat-value">32 km/h</div>
                        <Activity size={24} className="stat-icon" />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TrafficMonitoring;
