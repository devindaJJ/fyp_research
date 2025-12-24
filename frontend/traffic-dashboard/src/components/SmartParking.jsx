import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Search, Car, Bike, Truck, RefreshCw, X, ArrowRight, Info } from 'lucide-react';
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
        lat: 6.9344,
        lng: 79.8451,
        totalSlots: 250,
        availableSlots: 15,
        occupiedSlots: 235,
        type: ["Car", "Van"],
        lastUpdated: "5 seconds ago",
        status: "red"
    },
    {
        id: 2,
        name: "Bambalapitiya Parking Zone A",
        lat: 6.8981,
        lng: 79.8549,
        totalSlots: 120,
        availableSlots: 32,
        occupiedSlots: 88,
        type: ["Car", "Bike"],
        lastUpdated: "10 seconds ago",
        status: "yellow"
    },
    {
        id: 3,
        name: "Kandy City Center Mall Parking",
        lat: 7.2936,
        lng: 80.6350,
        totalSlots: 300,
        availableSlots: 180,
        occupiedSlots: 120,
        type: ["Car", "Van", "Bike"],
        lastUpdated: "2 minutes ago",
        status: "green"
    },
    {
        id: 4,
        name: "Galle Face Green Public Parking",
        lat: 6.9231,
        lng: 79.8447,
        totalSlots: 100,
        availableSlots: 8,
        occupiedSlots: 92,
        type: ["Car"],
        lastUpdated: "30 seconds ago",
        status: "red"
    },
    {
        id: 5,
        name: "Unity Plaza Parking, Bambalapitiya",
        lat: 6.8950,
        lng: 79.8555,
        totalSlots: 80,
        availableSlots: 45,
        occupiedSlots: 35,
        type: ["Bike", "Car"],
        lastUpdated: "1 minute ago",
        status: "green"
    }
];

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
    const [selectedLocation, setSelectedLocation] = useState(null);
    const [searchQuery, setSearchQuery] = useState("");
    const [vehicleType, setVehicleType] = useState("All");
    const [isAutoRefresh, setIsAutoRefresh] = useState(true);
    const [mapCenter, setMapCenter] = useState([6.9271, 79.8612]); // Colombo Center
    const [mapZoom, setMapZoom] = useState(13);

    const filteredLocations = parkingLocations.filter(loc => {
        const matchesSearch = loc.name.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = vehicleType === "All" || loc.type.includes(vehicleType);
        return matchesSearch && matchesType;
    });

    const handleLocationSelect = (loc) => {
        setSelectedLocation(loc);
        setMapCenter([loc.lat, loc.lng]);
        setMapZoom(16);
    };

    const handleSearchChange = (e) => {
        const value = e.target.value;
        setSearchQuery(value);

        // If searching and exactly matching a major city, jump there
        if (value.toLowerCase() === "kandy") {
            setMapCenter([7.2906, 80.6337]);
            setMapZoom(14);
        } else if (value.toLowerCase() === "colombo") {
            setMapCenter([6.9271, 79.8612]);
            setMapZoom(13);
        }
    };

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

                        <button className="details-btn">
                            View Detailed Analytics <ArrowRight size={18} />
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SmartParking;
