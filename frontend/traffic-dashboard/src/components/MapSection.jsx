import React from 'react';
import './MapSection.css';

const MapSection = () => {
    return (
        <div className="section map-section">
            {/* 
        In a real app, we would use Google Maps API or Leaflet.
        For now, we'll use an iframe or a placeholder image div to simulate the map view 
        of Sri Lanka as shown in the reference.
      */}
            <div className="map-container">
                <iframe
                    title="Map of Sri Lanka"
                    src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1983088.005179266!2d80.6!3d7.8!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3ae2593cf65a1e9d%3A0xe13da4b400e2d38c!2sSri%20Lanka!5e1!3m2!1sen!2slk!4v1700000000000!5m2!1sen!2slk"
                    width="100%"
                    height="450"
                    style={{ border: 0 }}
                    allowFullScreen=""
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                ></iframe>
            </div>
        </div>
    );
};

export default MapSection;
