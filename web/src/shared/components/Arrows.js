import React from 'react';
import PropTypes from 'prop-types';

const ArrowButton = ({ disabled, onClick, label, children }) => (
  <button
    type="button"
    aria-label={label}
    disabled={disabled}
    onClick={onClick}
    className={`inline-flex items-center justify-center w-10 h-10 rounded-full border transition
      ${disabled ? 'opacity-40 cursor-not-allowed border-gray-300 text-gray-400 dark:border-gray-700' : 'border-brand-400 text-brand-600 hover:bg-brand-50 dark:border-brandDark-400 dark:text-brandDark-300 dark:hover:bg-slate-800'}`}
  >
    {children}
  </button>
);

ArrowButton.propTypes = {
  disabled: PropTypes.bool,
  onClick: PropTypes.func,
  label: PropTypes.string,
  children: PropTypes.node,
};

ArrowButton.defaultProps = {
  disabled: false,
  onClick: () => {},
  label: '',
  children: null,
};

const Arrows = ({ page, onPrev, onNext, hasPrev, hasNext }) => (
  <div className="flex items-center justify-center gap-4 my-6">
    <ArrowButton disabled={!hasPrev} onClick={onPrev} label="Previous page">
      <span className="text-xl">◀</span>
    </ArrowButton>
    <div className="min-w-[4rem] text-center text-sm font-medium text-slate-700 dark:text-slate-200">
      Page {page}
    </div>
    <ArrowButton disabled={!hasNext} onClick={onNext} label="Next page">
      <span className="text-xl">▶</span>
    </ArrowButton>
  </div>
);

Arrows.propTypes = {
  page: PropTypes.number.isRequired,
  onPrev: PropTypes.func.isRequired,
  onNext: PropTypes.func.isRequired,
  hasPrev: PropTypes.bool,
  hasNext: PropTypes.bool,
};

Arrows.defaultProps = {
  hasPrev: false,
  hasNext: false,
};

export default Arrows;

