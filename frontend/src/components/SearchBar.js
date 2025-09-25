import React from 'react';
import PropTypes from 'prop-types';

const SearchBar = ({ searchTerm, onSearchChange, placeholder, compact, className }) => {
  const wrapperBase = compact
    ? 'mb-0 p-0 bg-transparent ring-0 shadow-none'
    : 'mb-8 p-4 bg-brand-50 dark:bg-gray-900 rounded-lg shadow-md ring-1 ring-brand-100 dark:ring-0';
  const inputBase = compact
    ? 'h-10 px-4 text-base rounded-md'
    : 'px-5 py-3 rounded-full text-lg';
  return (
    <div className={`${wrapperBase} ${className || ''}`}>
      <input
        type="text"
        placeholder={placeholder}
        value={searchTerm}
        onChange={onSearchChange}
        className={`w-full bg-white text-slate-900 border border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition duration-200 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:focus:ring-brandDark-500 dark:focus:border-brandDark-500 ${inputBase}`}
      />
    </div>
  );
};

SearchBar.propTypes = {
  searchTerm: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  compact: PropTypes.bool,
  className: PropTypes.string,
};

SearchBar.defaultProps = {
  placeholder: 'Search...',
  compact: false,
  className: '',
};

export default SearchBar;
