// src/components/Header.js
import React from 'react';
import { Link } from 'react-router-dom';

function Header() {
  return (
    <header className="bg-blue-600 p-4 shadow-md">
      <nav className="container mx-auto flex justify-between items-center">
        <Link to="/" className="text-white text-2xl font-bold">
          My CD Collection
        </Link>
        <ul className="flex space-x-6">
          <li>
            <Link
              to="/" // Artist Browser is now the landing page
              className="text-white text-lg font-semibold hover:text-blue-200 transition duration-200"
            >
              Artist Browser
            </Link>
          </li>
          <li>
            <Link
              to="/download" // Corrected path to /download as per App.js
              className="text-white text-lg font-semibold hover:text-blue-200 transition duration-200"
            >
              My Downloads
            </Link>
          </li>
        </ul>
      </nav>
    </header>
  );
}

export default Header;