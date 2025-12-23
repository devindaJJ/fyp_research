import React, { useState } from 'react';
import { Search, Filter, Eye } from 'lucide-react';
import EvidenceModal from './EvidenceModal';
import './ViolationList.css';

const MOCK_DATA = [
    { id: 'V001', plate: 'WP CAM-1234', type: 'Speeding', speed: '85 km/h', limit: '60 km/h', location: 'Galle Road, Colombo 3', date: '2025-10-24 14:30', status: 'Pending' },
    { id: 'V002', plate: 'WP CAB-5678', type: 'Lane Violation', speed: '-', limit: '-', location: 'Duplication Road', date: '2025-10-24 12:15', status: 'Reviewed' },
    { id: 'V003', plate: 'SP BCD-9988', type: 'Speeding', speed: '72 km/h', limit: '50 km/h', location: 'High Level Road', date: '2025-10-23 09:45', status: 'Pending' },
    { id: 'V004', plate: 'WP KW-4455', type: 'Speeding', speed: '90 km/h', limit: '60 km/h', location: 'Galle Road, Colombo 4', date: '2025-10-23 08:20', status: 'Pending' },
    { id: 'V005', plate: 'CP AB-1122', type: 'Lane Violation', speed: '-', limit: '-', location: 'Kandy Road', date: '2025-10-22 18:10', status: 'Reviewed' },
    { id: 'V006', plate: 'WP XY-7777', type: 'Speeding', speed: '110 km/h', limit: '70 km/h', location: 'Expressway E01', date: '2025-10-22 15:00', status: 'Pending' },
];

const ViolationList = () => {
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('All');
    const [filterLocation, setFilterLocation] = useState('All');
    const [selectedViolation, setSelectedViolation] = useState(null);

    const filteredData = MOCK_DATA.filter(item => {
        const matchesSearch = item.plate.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesType = filterType === 'All' || item.type === filterType;
        const matchesLocation = filterLocation === 'All' || item.location.includes(filterLocation);
        return matchesSearch && matchesType && matchesLocation;
    });

    return (
        <div className="violation-list">
            {/* Filters Bar */}
            <div className="filters-bar">
                <div className="search-box">
                    <Search size={18} />
                    <input
                        type="text"
                        placeholder="Search by Number Plate..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <div className="filter-group">
                    <div className="filter-item">
                        <Filter size={16} />
                        <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
                            <option value="All">All Types</option>
                            <option value="Speeding">Speeding</option>
                            <option value="Lane Violation">Lane Violation</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <select value={filterLocation} onChange={(e) => setFilterLocation(e.target.value)}>
                            <option value="All">All Locations</option>
                            <option value="Col">Colombo</option>
                            <option value="Galle">Galle Road</option>
                            <option value="Exp">Expressway</option>
                        </select>
                    </div>

                    <div className="filter-item">
                        <input type="date" className="date-input" />
                    </div>
                </div>
            </div>

            {/* Table */}
            <div className="table-container">
                <table className="v-table">
                    <thead>
                        <tr>
                            <th>Violation ID</th>
                            <th>Number Plate</th>
                            <th>Type</th>
                            <th>Speed</th>
                            <th>Limit</th>
                            <th>Location</th>
                            <th>Date & Time</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredData.map((row) => (
                            <tr key={row.id}>
                                <td className="fw-bold">
                                    <span className="id-badge">{row.id}</span>
                                </td>
                                <td className="fw-bold">{row.plate}</td>
                                <td>
                                    <span className={`type-badge ${row.type === 'Speeding' ? 'speeding' : 'lane'}`}>
                                        {row.type}
                                    </span>
                                </td>
                                <td className={row.type === 'Speeding' ? 'text-danger' : ''}>{row.speed}</td>
                                <td>{row.limit}</td>
                                <td>{row.location}</td>
                                <td>{row.date}</td>
                                <td>
                                    <span className={`status-badge ${row.status.toLowerCase()}`}>
                                        {row.status}
                                    </span>
                                </td>
                                <td>
                                    <button
                                        className="action-btn"
                                        title="View Details"
                                        onClick={() => setSelectedViolation(row)}
                                    >
                                        <Eye size={18} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {filteredData.length === 0 && (
                            <tr>
                                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>
                                    No violations found matching filters.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Evidence Modal */}
            {selectedViolation && (
                <EvidenceModal
                    violation={selectedViolation}
                    onClose={() => setSelectedViolation(null)}
                />
            )}
        </div>
    );
};

export default ViolationList;
