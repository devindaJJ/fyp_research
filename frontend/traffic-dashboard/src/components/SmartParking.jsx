import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Search, Car, Bike, Truck, RefreshCw, X, ArrowRight, Info, MapPin, ArrowLeft } from 'lucide-react';
import 'leaflet/dist/leaflet.css';
import './SmartParking.css';

// Fix for default marker icons in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Mock Data for Parking Locations in Sri Lanka
const parkingLocations = [
    {
        id: 1,
        name: "Colombo Fort Central Parking",
        address: "Fort, Colombo 01",
        lat: 6.9344,
        lng: 79.8451,
        totalSlots: 250,
        availableSlots: 15,
        occupiedSlots: 220,
        reservedSlots: 10,
        disabledSlots: 5,
        type: ["Car", "Van"],
        lastUpdated: "5 seconds ago",
        status: "red"
    },
    {
        id: 2,
        name: "Bambalapitiya Parking Zone A",
        address: "Galle Road, Bambalapitiya",
        lat: 6.8981,
        lng: 79.8549,
        totalSlots: 120,
        availableSlots: 32,
        occupiedSlots: 78,
        reservedSlots: 8,
        disabledSlots: 2,
        type: ["Car", "Bike"],
        lastUpdated: "10 seconds ago",
        status: "yellow"
    },
    {
        id: 3,
        name: "Kandy City Center Mall Parking",
        address: "Dalada Veediya, Kandy",
        lat: 7.2936,
        lng: 80.6350,
        totalSlots: 300,
        availableSlots: 180,
        occupiedSlots: 100,
        reservedSlots: 15,
        disabledSlots: 5,
        type: ["Car", "Van", "Bike"],
        lastUpdated: "2 minutes ago",
        status: "green"
    },
    {
        id: 4,
        name: "Galle Face Green Public Parking",
        address: "Galle Face, Colombo 03",
        lat: 6.9231,
        lng: 79.8447,
        totalSlots: 100,
        availableSlots: 8,
        occupiedSlots: 85,
        reservedSlots: 5,
        disabledSlots: 2,
        type: ["Car"],
        lastUpdated: "30 seconds ago",
        status: "red"
    },
    {
        id: 5,
        name: "Unity Plaza Parking, Bambalapitiya",
        address: "Bambalapitiya, Colombo 04",
        lat: 6.8950,
        lng: 79.8555,
        totalSlots: 80,
        availableSlots: 45,
        occupiedSlots: 30,
        reservedSlots: 3,
        disabledSlots: 2,
        type: ["Bike", "Car"],
        lastUpdated: "1 minute ago",
        status: "green"
    }
];

// Mock for Slot Details
const generateSlots = (count) => {
    const statuses = ["available", "occupied", "reserved", "disabled"];
    return Array.from({ length: count }, (_, i) => {
        const weight = Math.random();
        let status;
        if (weight < 0.4) status = "available";
        else if (weight < 0.8) status = "occupied";
        else if (weight < 0.9) status = "reserved";
        else status = "disabled";

        return {
            id: `${String.fromCharCode(65 + Math.floor(i / 10))}${i % 10 + 1}`,
            status: status,
            vehicleNo: status === "occupied" ? `WP ${['CAA', 'CBB', 'KCC', 'CAD'][Math.floor(Math.random() * 4)]}-${Math.floor(1000 + Math.random() * 9000)}` : null,
            parkedTime: status === "occupied" ? `${Math.floor(Math.random() * 12 + 1)}:${Math.floor(Math.random() * 60).toString().padStart(2, '0')} AM` : null,
            duration: status === "occupied" ? `${Math.floor(Math.random() * 3)}h ${Math.floor(Math.random() * 60)}m` : null
        };
    });
};

// Helper to create custom marker icons
const createCustomIcon = (status) => {
    return new L.DivIcon({
        className: `custom-marker marker-${status}`,
        html: `<div class="marker-pin"></div>`,
        iconSize: [30, 42],
        iconAnchor: [15, 42]
    });
};

// Component to handle map view updates
function MapViewUpdater({ center, zoom }) {
    const map = useMap();
    useEffect(() => {
        map.setView(center, zoom);
    }, [center, zoom, map]);
    return null;
}

const SmartParking = () => {
    const [view, setView] = useState('map'); // 'map' or 'details'
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [vehicleType, setVehicleType] = useState("All");
    const [isAutoRefresh, setIsAutoRefresh] = useState(true);
    const [mapCenter, setMapCenter] = useState([6.9271, 79.8612]); // Colombo Center
    const [mapZoom, setMapZoom] = useState(13);
    const [activeSlot, setActiveSlot] = useState(null);
    const [slots, setSlots] = useState([]);

    const filteredLocations = parkingLocations.filter(loc => {
        const matchesSearch = loc.name.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = vehicleType === "All" || loc.type.includes(vehicleType);
        return matchesSearch && matchesType;
    });

    const handleViewDetails = (loc) => {
        setSelectedLocation(loc);
        setSlots(generateSlots(40)); // Generate slots for the demo
        setView('details');
    };

    const handleSearchChange = (e) => {
        const value = e.target.value;
        setSearchQuery(value);

        if (value.toLowerCase() === "kandy") {
            setMapCenter([7.2906, 80.6337]);
            setMapZoom(14);
        } else if (value.toLowerCase() === "colombo") {
            setMapCenter([6.9271, 79.8612]);
            setMapZoom(13);
        }
    };

    if (view === 'details' && selectedLocation) {
        return (
            <div className="smart-parking-container">
                <button className="back-btn" onClick={() => setView('map')}>
                    <ArrowLeft size={18} /> Back to Live Map
                </button>

                <div className="parking-overview-container">
                    {/* Left Panel: Stats */}
                    <div className="details-left-panel">
                        <div className="location-header">
                            <h2>{selectedLocation.name}</h2>
                            <div className="location-address">
                                <MapPin size={16} /> {selectedLocation.address}
                            </div>
                        </div>

                        <div className="summary-grid">
                            <div className="summary-card total">
                                <span className="summary-label">Total Slots</span>
                                <span className="summary-value">{selectedLocation.totalSlots}</span>
                            </div>
                            <div className="summary-card available">
                                <span className="summary-label">Available</span>
                                <span className="summary-value">{selectedLocation.availableSlots}</span>
                            </div>
                            <div className="summary-card reserved">
                                <span className="summary-label">Reserved</span>
                                <span className="summary-value">{selectedLocation.reservedSlots}</span>
                            </div>
                            <div className="summary-card disabled">
                                <span className="summary-label">Disabled</span>
                                <span className="summary-value">{selectedLocation.disabledSlots}</span>
                            </div>
                        </div>

                        <div className="info-card-overlay" style={{ position: 'static', width: '100%', padding: '24px', background: 'rgba(30, 41, 59, 0.4)' }}>
                            <div className="update-status">
                                <div className="pulse"></div>
                                Live Feedback System Active
                            </div>
                            <p style={{ color: '#94a3b8', fontSize: '14px', lineHeight: '1.6' }}>
                                Interactive slot monitoring enabled. Hover over individual slots to view vehicle information and parking duration.
                            </p>
                        </div>
                    </div>

                    {/* Right Panel: Grid */}
                    <div className="details-right-panel">
                        <div className="grid-header">
                            <h3>Parking Slot Layout</h3>
                            <div className="legend">
                                <div className="legend-item"><div className="dot available"></div> Available</div>
                                <div className="legend-item"><div className="dot occupied"></div> Occupied</div>
                                <div className="legend-item"><div className="dot reserved"></div> Reserved</div>
                                <div className="legend-item"><div className="dot disabled"></div> Disabled</div>
                            </div>
                        </div>

                        <div className="slots-grid">
                            {slots.map(slot => (
                                <div
                                    key={slot.id}
                                    className={`parking-slot ${slot.status} ${activeSlot?.id === slot.id ? 'active' : ''}`}
                                    onMouseEnter={() => slot.status !== 'disabled' && setActiveSlot(slot)}
                                    onMouseLeave={() => setActiveSlot(null)}
                                >
                                    {slot.id}
                                    {activeSlot?.id === slot.id && (
                                        <div className="slot-tooltip">
                                            <div className="tooltip-line">
                                                <span className="tooltip-label">Slot:</span>
                                                <span className="tooltip-value">{slot.id}</span>
                                            </div>
                                            {slot.status === 'occupied' ? (
                                                <>
                                                    <div className="tooltip-line">
                                                        <span className="tooltip-label">Vehicle:</span>
                                                        <span className="tooltip-value">{slot.vehicleNo}</span>
                                                    </div>
                                                    <div className="tooltip-line">
                                                        <span className="tooltip-label">Time:</span>
                                                        <span className="tooltip-value">{slot.parkedTime}</span>
                                                    </div>
                                                    <div className="tooltip-line">
                                                        <span className="tooltip-label">Duration:</span>
                                                        <span className="tooltip-value">{slot.duration}</span>
                                                    </div>
                                                </>
                                            ) : (
                                                <div style={{ color: slot.status === 'available' ? '#10b981' : '#3b82f6', fontWeight: 600, fontSize: '12px', marginTop: '4px' }}>
                                                    {slot.status.charAt(0).toUpperCase() + slot.status.slice(1)}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="smart-parking-container">
            {/* Top Filter Bar */}
            <div className="filter-bar">
                <div className="filters-left">
                    <div className="filter-group">
                        <label>Location</label>
                        <div style={{ position: 'relative' }}>
                            <Search size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#64748b' }} />
                            <input
                                type="text"
                                className="filter-input"
                                placeholder="Search city or zone..."
                                style={{ paddingLeft: 34 }}
                                value={searchQuery}
                                onChange={handleSearchChange}
                            />
                        </div>
                    </div>

                    <div className="filter-group">
                        <label>Vehicle Type</label>
                        <select
                            className="filter-select"
                            value={vehicleType}
                            onChange={(e) => setVehicleType(e.target.value)}
                        >
                            <option value="All">All Types</option>
                            <option value="Car">Car</option>
                            <option value="Bike">Bike</option>
                            <option value="Van">Van</option>
                        </select>
                    </div>
                </div>

                <div
                    className={`refresh-toggle ${isAutoRefresh ? 'active' : ''}`}
                    onClick={() => setIsAutoRefresh(!isAutoRefresh)}
                >
                    <RefreshCw size={16} className={isAutoRefresh ? 'animate-spin' : ''} style={{ color: isAutoRefresh ? '#3b82f6' : '#64748b' }} />
                    <span>Auto-refresh: {isAutoRefresh ? 'ON' : 'OFF'}</span>
                </div>
            </div>

            {/* Map Section */}
            <div className="parking-map-wrapper">
                <MapContainer
                    center={mapCenter}
                    zoom={mapZoom}
                    zoomControl={false}
                    scrollWheelZoom={true}
                    style={{ height: '100%', width: '100%' }}
                >
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    />
                    <MapViewUpdater center={mapCenter} zoom={mapZoom} />

                    {filteredLocations.map(loc => (
                        <Marker
                            key={loc.id}
                            position={[loc.lat, loc.lng]}
                            icon={createCustomIcon(loc.status)}
                            eventHandlers={{
                                click: () => setSelectedLocation(loc),
                            }}
                        >
                            <Popup>
                                <div style={{ color: '#000' }}>
                                    <strong>{loc.name}</strong><br />
                                    Available: {loc.availableSlots}
                                </div>
                            </Popup>
                        </Marker>
                    ))}
                </MapContainer>

                {/* Location Info Card */}
                {selectedLocation && (
                    <div className="info-card-overlay">
                        <div className="info-card-header">
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#3b82f6', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
                                    <Info size={14} />
                                    PARKING ZONE
                                </div>
                                <h3>{selectedLocation.name}</h3>
                            </div>
                            <button className="close-btn" onClick={() => setSelectedLocation(null)}>
                                <X size={20} />
                            </button>
                        </div>

                        <div className="info-stats">
                            <div className="stat-item">
                                <span className="stat-label">Total</span>
                                <span className="stat-value">{selectedLocation.totalSlots}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Available</span>
                                <span className="stat-value available">{selectedLocation.availableSlots}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Occupied</span>
                                <span className="stat-value occupied">{selectedLocation.occupiedSlots}</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-label">Type</span>
                                <span className="stat-value" style={{ fontSize: 14 }}>{selectedLocation.type.join(", ")}</span>
                            </div>
                        </div>

                        <div className="update-status">
                            <div className="pulse"></div>
                            Last Updated: {selectedLocation.lastUpdated}
                        </div>

                        <button className="details-btn" onClick={() => handleViewDetails(selectedLocation)}>
                            View Detailed Analytics <ArrowRight size={18} />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SmartParking;
