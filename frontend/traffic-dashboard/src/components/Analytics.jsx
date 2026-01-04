import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { MoreHorizontal } from 'lucide-react';
import './Analytics.css';

const dataBar = [
    { name: 'Jan 1', uv: 2000 },
    { name: 'Jan 2', uv: 5000 },
    { name: 'Jan 15', uv: 9000 },
    { name: 'Jan 16', uv: 7000 },
    { name: 'Jan 31', uv: 7500 },
    { name: 'Feb 6', uv: 10500 },
    { name: 'Feb 12', uv: 8000 },
    { name: 'Feb 16', uv: 5500 },
];

const dataPie = [
    { name: 'France', value: 400 },
    { name: 'Ireland', value: 300 },
    { name: 'Poland', value: 300 },
    { name: 'USA', value: 200 },
];

const COLORS = ['#2251cc', '#00C49F', '#FFBB28', '#FF8042'];

const Analytics = () => {
    return (
        <div className="section analytics-section">
            <h2 className="section-title">Analytics & Reports</h2>

            <div className="analytics-controls">
                <div className="tab-group">
                    <span className="active">Dashboards</span>
                    <span>Real-time dashboards <span className="badge">BETA</span></span>
                    <span>Reports</span>
                    <span>Custom reports</span>
                </div>
                <div className="date-picker">
                    January 1, 2024 - February 16, 2024
                </div>
            </div>

            <div className="stats-overview">
                <div className="stat-card">
                    <div className="stat-header">
                        <h3>Page views</h3>
                        <MoreHorizontal size={16} />
                    </div>
                    <div className="stat-value">12,178</div>
                    <div className="stat-chart-placeholder"></div>
                </div>
                <div className="stat-card">
                    <div className="stat-header">
                        <h3>Bounce rate</h3>
                        <MoreHorizontal size={16} />
                    </div>
                    <div className="stat-value">28.12%</div>
                </div>
                <div className="stat-card">
                    <div className="stat-header">
                        <h3>Visitors</h3>
                        <MoreHorizontal size={16} />
                    </div>
                    <div className="stat-value">1,450</div>
                </div>
            </div>

            <div className="charts-container">
                <div className="chart-wrapper main-chart">
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={dataBar}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} />
                            <XAxis dataKey="name" axisLine={false} tickLine={false} />
                            <YAxis axisLine={false} tickLine={false} />
                            <Tooltip cursor={{ fill: 'transparent' }} />
                            <Bar dataKey="uv" fill="#2251cc" radius={[4, 4, 0, 0]} barSize={40} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="chart-row">
                    {/* Secondary charts could go here. For now, matching image structure vaguely. */}
                    <div className="chart-wrapper half">
                        <h4>Top countries from where visitors are coming in</h4>
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={dataPie}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={40}
                                    outerRadius={70}
                                    fill="#8884d8"
                                    paddingAngle={5}
                                    dataKey="value"
                                >
                                    {dataPie.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Analytics;
