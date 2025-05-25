// src/components/SearchBar.js
import React from 'react';

function SearchBar({ searchTerm, onSearchChange, placeholder = "Search..." }) {
  return (
    <div className="mb-8 p-4 bg-white rounded-lg shadow-md">
      <input
        type="text"
        placeholder={placeholder}
        value={searchTerm}
        onChange={onSearchChange}
        className="w-full px-5 py-3 border border-gray-300 rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition duration-200"
      />
    </div>
  );
}

export default SearchBar;