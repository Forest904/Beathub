import React from 'react';
import PropTypes from 'prop-types';

const CancelDownloadButton = ({ onCancel, disabled }) => {
  return (
    <button
      type="button"
      onClick={onCancel}
      disabled={disabled}
      className={`text-sm px-3 py-2 rounded-md font-semibold whitespace-nowrap border ${
        disabled
          ? 'bg-red-200 text-white cursor-not-allowed border-red-300'
          : 'bg-red-600 hover:bg-red-700 text-white border-red-700'
      }`}
      title={disabled ? 'No active download to cancel' : 'Cancel current download'}
    >
      Cancel
    </button>
  );
};

CancelDownloadButton.propTypes = {
  onCancel: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

CancelDownloadButton.defaultProps = {
  disabled: false,
};

export default CancelDownloadButton;

