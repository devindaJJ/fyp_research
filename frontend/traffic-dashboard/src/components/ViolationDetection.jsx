import React, { useState } from 'react';
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Car, AlertTriangle, Gauge, Ban, LayoutDashboard, List, FileText, History, Bell } from 'lucide-react';
import ViolationList from './ViolationList';
import './ViolationDetection.css';

// Mock Data
const violationsPerHour = [
    { time: '00:00', count: 2 },
    { time: '04:00', count: 1 },
    { time: '08:00', count: 15 },
    { time: '12:00', count: 22 },
    { time: '16:00', count: 28 },
    { time: '20:00', count: 10 },
    { time: '23:59', count: 5 },
];

const violationTypes = [
    { name: 'Speeding', value: 65 },
    { name: 'Lane Violation', value: 35 },
];

const weeklyTrend = [
    { day: 'Mon', violations: 45 },
    { day: 'Tue', violations: 52 },
    { day: 'Wed', violations: 38 },
    { day: 'Thu', violations: 65 },
    { day: 'Fri', violations: 72 },
    { day: 'Sat', violations: 48 },
    { day: 'Sun', violations: 30 },
];

const COLORS = ['#FF8042', '#00C49F'];

const ViolationDetection = () => {
    const [viewMode, setViewMode] = useState('stats'); // 'stats' | 'list' | 'reports' | 'history' | 'notifications'
    const [notificationCount] = useState(3);

    const renderContent = () => {
        switch (viewMode) {
            case 'stats':
                return (
                    <>
                        {/* Overview Cards */}
                        <div className="violation-stats-grid">
                            <div className="v-card">
                                <div className="v-card-icon blue"><Car size={24} /></div>
                                <div className="v-card-info">
                                    <h3>Total Vehicles</h3>
                                    <p className="v-number">14,205</p>
                                    <span className="v-sub">Today</span>
                                </div>
                            </div>

                            <div className="v-card">
                                <div className="v-card-icon red"><AlertTriangle size={24} /></div>
                                <div className="v-card-info">
                                    <h3>Total Violations</h3>
                                    <p className="v-number">342</p>
                                    <span className="v-sub">2.4% rate</span>
                                </div>
                            </div>

                            <div className="v-card">
                                <div className="v-card-icon orange"><Gauge size={24} /></div>
                                <div className="v-card-info">
                                    <h3>Speeding</h3>
                                    <p className="v-number">215</p>
                                    <span className="v-sub">High Severity</span>
                                </div>
                            </div>

                            <div className="v-card">
                                <div className="v-card-icon yellow"><Ban size={24} /></div>
                                <div className="v-card-info">
                                    <h3>Lane Violations</h3>
                                    <p className="v-number">127</p>
                                    <span className="v-sub">Moderate Severity</span>
                                </div>
                            </div>
                        </div>

                        {/* Charts Section */}
                        <div className="violation-charts-grid">
                            {/* Violations Per Hour */}
                            <div className="chart-card large">
                                <h3>Violations Per Hour</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <AreaChart data={violationsPerHour}>
                                        <defs>
                                            <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#2251cc" stopOpacity={0.8} />
                                                <stop offset="95%" stopColor="#2251cc" stopOpacity={0} />
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="time" />
                                        <YAxis />
                                        <Tooltip />
                                        <Area type="monotone" dataKey="count" stroke="#2251cc" fillOpacity={1} fill="url(#colorCount)" />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Speeding vs Lane */}
                            <div className="chart-card">
                                <h3>Violation Distribution</h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <PieChart>
                                        <Pie
                                            data={violationTypes}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {violationTypes.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))}
                                        </Pie>
                                        <Tooltip />
                                        <Legend />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>

                            {/* Weekly Trend */}
                            <div className="chart-card full-width">
                                <h3>Weekly Violation Trend</h3>
                                <ResponsiveContainer width="100%" height={250}>
                                    <BarChart data={weeklyTrend}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="day" />
                                        <YAxis />
                                        <Tooltip />
                                        <Bar dataKey="violations" fill="#161e54" radius={[4, 4, 0, 0]} barSize={50} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </>
                );
            case 'list':
                return <ViolationList />;
            case 'reports':
                return (
                    <div className="placeholder-view">
                        <FileText size={64} color="#bdc3c7" />
                        <h3>Reports Generation</h3>
                        <p>Generate daily, weekly, and monthly traffic violation reports here.</p>
                        <button className="btn primary">Create New Report</button>
                    </div>
                );
            case 'history':
                return (
                    <div className="placeholder-view">
                        <History size={64} color="#bdc3c7" />
                        <h3>Violation History</h3>
                        <p>View historical logs and archived violation records.</p>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="section violation-section">
            <div className="section-header-row">
                <h2 className="section-title">Violation Detection</h2>
                <div className="view-toggle">
                    <button
                        className={`toggle-btn ${viewMode === 'stats' ? 'active' : ''}`}
                        onClick={() => setViewMode('stats')}
                    >
                        <LayoutDashboard size={18} />
                        Overview
                    </button>
                    <button
                        className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                        onClick={() => setViewMode('list')}
                    >
                        <List size={18} />
                        Violations Detected
                    </button>
                    <button
                        className={`toggle-btn ${viewMode === 'reports' ? 'active' : ''}`}
                        onClick={() => setViewMode('reports')}
                    >
                        <FileText size={18} />
                        Reports
                    </button>
                    <button
                        className={`toggle-btn ${viewMode === 'history' ? 'active' : ''}`}
                        onClick={() => setViewMode('history')}
                    >
                        <History size={18} />
                        History
                    </button>
                </div>
            </div>

            {renderContent()}
        </div>
    );
};

export default ViolationDetection;
