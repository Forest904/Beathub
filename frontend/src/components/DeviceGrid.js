import React from 'react';
import PropTypes from 'prop-types';

const StatusPill = ({ ok, label, className }) => {
  const stateClass = ok ? 'bg-green-700 text-green-100' : 'bg-gray-700 text-gray-300';
  const classes = `inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${stateClass} ${className}`.trim();
  return (
    <span className={classes}>
      {label}
    </span>
  );
};

StatusPill.propTypes = {
  ok: PropTypes.bool.isRequired,
  label: PropTypes.string.isRequired,
  className: PropTypes.string,
};

StatusPill.defaultProps = {
  className: '',
};

const DriveIcon = () => (
  <svg
    className="w-12 h-12 text-blue-400 drop-shadow"
    viewBox="0 0 64 64"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <rect x="6" y="16" width="52" height="32" rx="6" ry="6" fill="currentColor" opacity="0.18" />
    <rect
      x="10"
      y="20"
      width="44"
      height="24"
      rx="4"
      ry="4"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    />
    <circle cx="48" cy="32" r="5" fill="currentColor" opacity="0.35" />
    <circle cx="48" cy="32" r="2" fill="currentColor" />
    <rect x="18" y="44" width="28" height="4" rx="2" fill="currentColor" opacity="0.45" />
  </svg>
);

const DeviceGrid = ({ devices, onSelect }) => {
  if (!devices || devices.length === 0) {
    return <div className="text-gray-400">No connected burner detected.</div>;
  }

  const handleCardToggle = (device) => {
    if (!onSelect || device.active) {
      return;
    }
    if (device.selected) {
      onSelect(null);
    } else {
      onSelect(device);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {devices.map((device) => {
        const isSelected = Boolean(device.selected);
        const isActive = Boolean(device.active);
        const cardClasses = [
          'group',
          'relative rounded-xl border p-5 bg-gray-800 transition-all duration-200',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-400 focus-visible:ring-offset-gray-900',
          isActive ? 'border-yellow-500/80 cursor-not-allowed opacity-70' : 'cursor-pointer hover:border-blue-400 hover:shadow-lg hover:shadow-blue-500/10',
          isSelected ? 'border-blue-500 shadow-lg shadow-blue-500/20 ring-1 ring-blue-500/40' : 'border-gray-700',
        ].join(' ');

        return (
          <div
            key={device.id}
            role={isActive ? undefined : 'button'}
            tabIndex={isActive ? -1 : 0}
            onClick={() => handleCardToggle(device)}
            onKeyDown={(event) => {
              if (isActive) {
                return;
              }
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleCardToggle(device);
              }
            }}
            className={cardClasses}
            aria-pressed={isSelected}
          >
            <div className="flex items-start justify-between">
              <div className="flex flex-col">
                <h3 className="text-lg font-semibold text-white">{device.display_name || device.id}</h3>
              </div>
              {isActive && <span className="text-xs font-semibold text-yellow-400">Active</span>}
              {!isActive && isSelected && <span className="text-xs font-semibold text-blue-300">Selected</span>}
            </div>
            <div className="mt-4 flex items-start gap-4">
              <div className="flex-shrink-0">
                <DriveIcon />
              </div>
              <div className="flex-1 flex flex-col gap-2 text-sm text-gray-200">
                <StatusPill
                  ok={Boolean(device.present)}
                  label={device.present ? 'Disc Present' : 'No Disc'}
                  className="w-fit"
                />
                <StatusPill
                  ok={Boolean(device.writable)}
                  label={device.writable ? 'Writable' : 'Not Writable'}
                  className="w-fit"
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

DeviceGrid.propTypes = {
  devices: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      display_name: PropTypes.string,
      active: PropTypes.bool,
      selected: PropTypes.bool,
      present: PropTypes.bool,
      writable: PropTypes.bool,
      volume_paths: PropTypes.arrayOf(PropTypes.string),
    }),
  ),
  onSelect: PropTypes.func,
};

DeviceGrid.defaultProps = {
  devices: [],
  onSelect: undefined,
};

export default DeviceGrid;
