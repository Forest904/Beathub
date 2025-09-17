import React from 'react';
import PropTypes from 'prop-types';

const SearchBar = ({ searchTerm, onSearchChange, placeholder }) => (
  <div className="mb-8 p-4 bg-gray-900 rounded-lg shadow-md">
    <input
      type="text"
      placeholder={placeholder}
      value={searchTerm}
      onChange={onSearchChange}
      className="w-full px-5 py-3 bg-gray-700 text-white border border-gray-600 rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
    />
  </div>
);

SearchBar.propTypes = {
  searchTerm: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
};

SearchBar.defaultProps = {
  placeholder: 'Search...',
};

export default SearchBar;
