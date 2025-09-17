import React from 'react';
import PropTypes from 'prop-types';
import DeviceGrid from './DeviceGrid';

const StatusRow = ({ label, ok }) => (
  <div className="flex items-center justify-between text-sm mb-1">
    <span className="text-gray-300">{label}</span>
    <span className={ok ? 'text-green-400' : 'text-red-400'}>{ok ? 'Yes' : 'No'}</span>
  </div>
);

StatusRow.propTypes = {
  label: PropTypes.string.isRequired,
  ok: PropTypes.bool.isRequired,
};

const BurnerIcon = () => (
  <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="28" stroke="#9CA3AF" strokeWidth="2" />
    <circle cx="32" cy="32" r="8" stroke="#60A5FA" strokeWidth="2" />
    <circle cx="32" cy="32" r="2" fill="#60A5FA" />
    <path d="M8 50h20" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

const DevicesPanel = ({ devices, loading, onSelect, burnerStatus }) => {
  const selected = devices?.find((device) => device.selected);

  const statusClassName = (() => {
    if (burnerStatus?.current_status === 'Burner Ready') {
      return 'text-green-400';
    }
    if (burnerStatus?.is_burning) {
      return 'text-yellow-400';
    }
    if (burnerStatus?.last_error) {
      return 'text-red-400';
    }
    return 'text-gray-300';
  })();

  return (
    <div className="bg-gray-800 rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-semibold mb-4">Devices</h2>
      {loading ? <p className="text-gray-400">Scanning devices...</p> : <DeviceGrid devices={devices} onSelect={onSelect} />}

      {selected && (
        <div className="mt-6 border border-gray-700 rounded p-4">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-lg font-semibold">Burner Device</h3>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex-shrink-0">
              <BurnerIcon />
            </div>
            <div className="flex-1">
              <div className="text-sm text-gray-300 mb-2">
                <span className="text-gray-400">Device:</span>
                <span className="text-white"> {selected.display_name || selected.id}</span>
              </div>
              <div className="text-sm text-gray-300 mb-3">
                <span className="text-gray-400">Status:</span>
                <span className={`ml-1 ${statusClassName}`}>
                  {burnerStatus?.current_status || 'Unknown'}
                </span>
              </div>
              <StatusRow label="Disc Present" ok={Boolean(selected.present)} />
              <StatusRow label="Writable" ok={Boolean(selected.writable)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

DevicesPanel.propTypes = {
  devices: DeviceGrid.propTypes.devices,
  loading: PropTypes.bool,
  onSelect: PropTypes.func,
  burnerStatus: PropTypes.shape({
    current_status: PropTypes.string,
    is_burning: PropTypes.bool,
    last_error: PropTypes.string,
  }),
};

DevicesPanel.defaultProps = {
  devices: [],
  loading: false,
  onSelect: undefined,
  burnerStatus: undefined,
};

export default DevicesPanel;
