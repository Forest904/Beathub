// frontend/src/components/Header.js

import React from 'react';
import { Link } from 'react-router-dom'; 

function Header() {
    return (
        <header className="bg-gray-800 text-white p-4 shadow-md">
            <div className="container mx-auto flex justify-between items-center">
                <Link to="/" className="text-2xl font-bold text-blue-400 hover:text-blue-300 transition duration-150">
                    Spotify Download Manager
                </Link>
                <nav>
                    <ul className="flex space-x-6">
                        <li>
                            <Link to="/browse" className="hover:text-blue-400 transition duration-150">
                                Artists
                            </Link>
                        </li>
                        <li>
                            <Link to="/download" className="hover:text-blue-400 transition duration-150">
                                Download
                            </Link>
                        </li>
                        <li>
                            <Link to="/burn-cd" className="hover:text-blue-400 transition duration-150">
                                CD Burner
                            </Link>
                        </li>
                    </ul>
                </nav>
            </div>
        </header>
    );
}

export default Header;