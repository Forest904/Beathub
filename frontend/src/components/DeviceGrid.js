import React from 'react';
import PropTypes from 'prop-types';

const StatusPill = ({ ok, label }) => {
  const stateClass = ok ? 'bg-green-700 text-green-100' : 'bg-gray-700 text-gray-300';
  return <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${stateClass} mr-2`}>{label}</span>;
};

StatusPill.propTypes = {
  ok: PropTypes.bool.isRequired,
  label: PropTypes.string.isRequired,
};

const DeviceGrid = ({ devices, onSelect }) => {
  if (!devices || devices.length === 0) {
    return <div className="text-gray-400">No connected burner detected.</div>;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {devices.map((device) => (
        <div key={device.id} className="border border-gray-700 rounded p-4 bg-gray-800">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-semibold text-white">{device.display_name || device.id}</div>
              <div className="text-xs text-gray-400">{device.id}</div>
            </div>
            {device.active ? (
              <span className="text-yellow-400 text-sm font-semibold">Active</span>
            ) : device.selected ? (
              <span className="text-blue-400 text-sm font-semibold">Selected</span>
            ) : (
              <button
                type="button"
                className="text-sm bg-blue-700 hover:bg-blue-800 text-white px-3 py-1 rounded"
                onClick={() => onSelect?.(device)}
              >
                Select
              </button>
            )}
          </div>
          <div className="mb-2">
            <StatusPill ok={Boolean(device.present)} label={device.present ? 'Disc Present' : 'No Disc'} />
            <StatusPill ok={Boolean(device.writable)} label={device.writable ? 'Writable' : 'Not Writable'} />
          </div>
          {device.volume_paths?.length > 0 && (
            <div className="text-xs text-gray-400">{device.volume_paths.join(' - ')}</div>
          )}
        </div>
      ))}
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
