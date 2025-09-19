import React from 'react';
import PropTypes from 'prop-types';
import { ReactComponent as CdRomIcon } from '../assets/icons/cd-rom.svg';

const StatusPill = ({ ok, label, className }) => {
  const stateClass = ok ? 'bg-green-700 text-green-100' : 'bg-gray-700 text-gray-300';
  // Doubled size and fixed width for equal sizing
  const classes = `inline-flex items-center justify-center px-4 py-2 rounded text-base font-semibold w-40 ${stateClass} ${className}`.trim();
  return <span className={classes}>{label}</span>;
};

StatusPill.propTypes = {
  ok: PropTypes.bool.isRequired,
  label: PropTypes.string.isRequired,
  className: PropTypes.string,
};

StatusPill.defaultProps = {
  className: '',
};


const DeviceCard = ({ device, onSelect, disabled }) => {
  const isSelected = Boolean(device?.selected);
  const isActive = Boolean(device?.active);

  const handleToggle = () => {
    if (!onSelect || isActive || disabled) return;
    if (isSelected) {
      onSelect(null);
    } else {
      onSelect(device);
    }
  };

  return (
    <div
      role={isActive || disabled ? undefined : 'button'}
      tabIndex={isActive || disabled ? -1 : 0}
      onClick={handleToggle}
      onKeyDown={(event) => {
        if (isActive || disabled) return;
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleToggle();
        }
      }}
      aria-pressed={isSelected}
      aria-disabled={isActive || disabled}
      className={`bg-gray-800 rounded-lg shadow-md overflow-hidden transform transition duration-200 w-full max-w-sm ${
        isActive || disabled ? 'cursor-not-allowed opacity-70' : 'hover:scale-105 cursor-pointer'
      } ${isSelected ? 'border-4 border-blue-500' : 'border-2 border-transparent'}`}
    >
      <div className="p-5">
        <h3 className="text-lg font-semibold text-white text-center">{device.display_name || device.id}</h3>
        <div className="mt-4 flex items-center justify-between">
          <CdRomIcon className="w-24 h-24 text-blue-400 drop-shadow" aria-hidden="true" />
          <div className="flex flex-col gap-2 text-sm text-gray-200 items-end">
            {isActive && <StatusPill ok label="In Use" className="!bg-amber-600 !text-black" />}
            <StatusPill ok={Boolean(device.present)} label={device.present ? 'Disc Present' : 'No Disc'} />
            <StatusPill ok={Boolean(device.writable)} label={device.writable ? 'Writable' : 'Not Writable'} />
          </div>
        </div>
      </div>
    </div>
  );
};

DeviceCard.propTypes = {
  device: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    display_name: PropTypes.string,
    active: PropTypes.bool,
    selected: PropTypes.bool,
    present: PropTypes.bool,
    writable: PropTypes.bool,
  }).isRequired,
  onSelect: PropTypes.func,
  disabled: PropTypes.bool,
};

DeviceCard.defaultProps = {
  onSelect: undefined,
  disabled: false,
};

export default DeviceCard;
