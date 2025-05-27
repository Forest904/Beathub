// src/components/SearchBar.js
import React from 'react';

function SearchBar({ searchTerm, onSearchChange, placeholder = "Search..." }) {
  return (
    <div className="mb-8 p-4 bg-gray-900 rounded-lg shadow-md">
      <input
        type="text"
        placeholder={placeholder}
        value={searchTerm}
        onChange={onSearchChange}
        // Input styles for dark theme:
        // bg-gray-700 for input background
        // text-white for input text
        // border-gray-600 for border
        // focus:ring-blue-500 and focus:border-blue-500 for focus state
        className="w-full px-5 py-3 bg-gray-700 text-white border border-gray-600 rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
      />
    </div>
  );
}

export default SearchBar;