import React from 'react';
import './Header.css'; // We can use inline or a separate file. I'll use inline style objects or utility classes defined in index.css if simple. Or Create a CSS module?
// Let's use vanilla CSS in a separate file or just keep it simple with classes.

const Header = () => {
    return (
        <header className="app-header">
            <div className="header-content">
                <h1>Urban Traffic Management System</h1>
                <p className="header-description">
                    An Urban Traffic Management System helps control traffic in the city. It reduces traffic jams, prevents accidents, and makes travel easier. The system uses traffic lights, cameras, and sensors to keep roads safe and smooth.
                </p>
            </div>
        </header>
    );
};

export default Header;
