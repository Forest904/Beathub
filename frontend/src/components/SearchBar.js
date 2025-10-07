import React, { useRef } from 'react';
import PropTypes from 'prop-types';

const SearchBar = ({ searchTerm, onSearchChange, placeholder, compact, className, onClear }) => {
  const wrapperBase = compact
    ? 'mb-0 p-0 bg-transparent ring-0 shadow-none'
    : 'mb-8 p-4 bg-brand-50 dark:bg-gray-900 rounded-lg shadow-md ring-1 ring-brand-100 dark:ring-0';
  const inputBase = compact
    ? 'h-10 px-4 text-base rounded-md'
    : 'px-5 py-3 rounded-full text-lg';
  const inputRef = useRef(null);

  const handleClear = () => {
    if (onClear) {
      onClear();
    } else {
      onSearchChange({ target: { value: '' } });
    }
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className={`${wrapperBase} ${className || ''}`}>
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={searchTerm}
          onChange={onSearchChange}
          className={`w-full bg-white text-slate-900 border border-brand-300 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition duration-200 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:focus:ring-brandDark-500 dark:focus:border-brandDark-500 ${inputBase} pr-10`}
        />
        {searchTerm && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Clear search"
            className="absolute inset-y-0 right-2 flex items-center justify-center text-slate-400 hover:text-slate-600 transition duration-150 dark:text-gray-300 dark:hover:text-white"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

SearchBar.propTypes = {
  searchTerm: PropTypes.string.isRequired,
  onSearchChange: PropTypes.func.isRequired,
  placeholder: PropTypes.string,
  compact: PropTypes.bool,
  className: PropTypes.string,
  onClear: PropTypes.func,
};

SearchBar.defaultProps = {
  placeholder: 'Search...',
  compact: false,
  className: '',
  onClear: null,
};

export default SearchBar;
