import React from 'react';
import PropTypes from 'prop-types';

const SearchBar = ({ searchTerm, onSearchChange, placeholder }) => (
  <div className="mb-8 p-4 bg-brand-50 dark:bg-gray-900 rounded-lg shadow-md ring-1 ring-brand-100 dark:ring-0">
    <input
      type="text"
      placeholder={placeholder}
      value={searchTerm}
      onChange={onSearchChange}
      className="w-full px-5 py-3 bg-white text-slate-900 border border-brand-300 rounded-full text-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition duration-200 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:focus:ring-brandDark-500 dark:focus:border-brandDark-500"
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
