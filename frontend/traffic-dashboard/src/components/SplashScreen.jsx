import React from 'react';
import './SplashScreen.css';
import logo from '../assets/logo.png';

const SplashScreen = () => {
    return (
        <div className="splash-screen">
            <div className="splash-content">
                <img src={logo} alt="UTMS Logo" className="splash-logo" />
            </div>
        </div>
    );
};

export default SplashScreen;
