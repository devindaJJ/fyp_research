import React from 'react';
import { X, Play, ZoomIn, CheckCircle } from 'lucide-react';
import './EvidenceModal.css';
import evidenceImg from '../assets/evidence_mock.png';

const EvidenceModal = ({ violation, onClose, onReview }) => {
    if (!violation) return null;

    const isReviewed = violation.status === 'Reviewed';

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-container" onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <h3>Violation Evidence: {violation.id}</h3>
                            <span className={`status-badge ${violation.status.toLowerCase()}`}>
                                {violation.status}
                            </span>
                        </div>
                        <span className="modal-date">{violation.date} • {violation.location}</span>
                    </div>
                    <button className="close-btn" onClick={onClose}>
                        <X size={24} />
                    </button>
                </div>

                <div className="modal-body">
                    <div className="media-section">
                        <div className="image-container">
                            <h4>Captured Image</h4>
                            <div className="img-wrapper">
                                <img src={evidenceImg} alt="Traffic Camera Capture" />
                                <div className="bounding-box-overlay"></div>
                            </div>
                        </div>

                        <div className="secondary-media">
                            <div className="plate-zoom">
                                <h4><ZoomIn size={16} /> Number Plate</h4>
                                <div className="plate-crop">
                                    {/* In a real app, this would be a cropped version */}
                                    <img src={evidenceImg} alt="Zoomed Plate" style={{ objectFit: 'cover', objectPosition: '80% 80%', transform: 'scale(2)' }} />
                                </div>
                                <div className="plate-text">{violation.plate}</div>
                            </div>

                            <div className="video-clip">
                                <h4><Play size={16} /> Video Clip (5-10s)</h4>
                                <div className="video-placeholder">
                                    <div className="play-overlay">
                                        <Play size={32} fill="white" />
                                    </div>
                                    <img src={evidenceImg} alt="Video Thumbnail" className="video-thumb" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="details-section">
                        <div className="detail-item">
                            <span className="label">Observed Speed</span>
                            <span className="value red">{violation.speed}</span>
                        </div>
                        <div className="detail-item">
                            <span className="label">Speed Limit</span>
                            <span className="value">{violation.limit}</span>
                        </div>
                        <div className="detail-item">
                            <span className="label">Violation Type</span>
                            <span className="value">{violation.type}</span>
                        </div>
                        <div className="detail-item">
                            <span className="label">Vehicle Type</span>
                            <span className="value">Sedan (Car)</span>
                        </div>
                    </div>
                </div>

                <div className="modal-footer">
                    <button className="btn secondary" onClick={onClose}>Close</button>
                    {!isReviewed && (
                        <button
                            className="btn primary"
                            onClick={() => onReview(violation.id)}
                        >
                            Mark as Reviewed
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default EvidenceModal;
