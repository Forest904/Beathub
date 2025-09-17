import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const NAV_LINKS = [
  { label: 'Artists', to: '/browse' },
  { label: 'Download', to: '/download' },
  { label: 'Burner', to: '/burn-cd' },
];

const Header = () => (
  <header className="bg-gray-800 text-white p-4 shadow-md">
    <div className="container mx-auto flex justify-between items-center">
      <Link to="/" className="text-2xl font-bold text-blue-400 hover:text-blue-300 transition duration-150">
        CD Burner
      </Link>
      <nav>
        <ul className="flex space-x-6">
          {NAV_LINKS.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) =>
                  `transition duration-150 ${isActive ? 'text-blue-400 font-semibold' : 'hover:text-blue-400'}`
                }
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  </header>
);

export default Header;
