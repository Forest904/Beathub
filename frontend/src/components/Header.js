// src/components/Header.js
import React from 'react';
import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="bg-gray-900 p-4 shadow-xl"> {/* Darker background, more pronounced shadow */}
      <nav className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-white text-3xl font-extrabold tracking-wide"> {/* Larger, bolder text, wider tracking */}
          My Spotify Collection
        </Link>
        <ul className="flex space-x-8"> {/* Increased spacing between links */}
          <li>
            <Link
              to="/"
              className="text-gray-300 text-lg font-medium hover:text-green-400 transition duration-300 ease-in-out" // Subtle text, Spotify green hover
            >
              Artists
            </Link>
          </li>
          <li>
            <Link
              to="/download"
              className="text-gray-300 text-lg font-medium hover:text-green-400 transition duration-300 ease-in-out" // Subtle text, Spotify green hover
            >
              Downloads
            </Link>
          </li>
        </ul>
      </nav>
    </header>
  );
}

export default Header;