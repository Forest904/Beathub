// frontend/src/components/DevicesPanel.js
import React from 'react';
import DeviceGrid from './DeviceGrid';

function StatusRow({ label, ok }) {
  return (
    <div className="flex items-center justify-between text-sm mb-1">
      <span className="text-gray-300">{label}</span>
      <span className={ok ? 'text-green-400' : 'text-red-400'}>{ok ? 'Yes' : 'No'}</span>
    </div>
  );
}

function BurnerIcon() {
  // Simple CD/burner inline SVG icon
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="28" stroke="#9CA3AF" strokeWidth="2" />
      <circle cx="32" cy="32" r="8" stroke="#60A5FA" strokeWidth="2" />
      <circle cx="32" cy="32" r="2" fill="#60A5FA" />
      <path d="M8 50h20" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function DevicesPanel({
  devices,
  loading,
  onSelect,
  burnerStatus,
}) {
  const selected = (devices || []).find((d) => d.selected);
  return (
    <div className="bg-gray-800 rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-semibold mb-4">Devices</h2>
      {loading ? (
        <p className="text-gray-400">Scanning devices...</p>
      ) : (
        <DeviceGrid devices={devices} onSelect={onSelect} />
      )}

      {selected && (
        <div className="mt-6 border border-gray-700 rounded p-4">
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-lg font-semibold">Burner device</h3>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex-shrink-0">
              <BurnerIcon />
            </div>
            <div className="flex-1">
              <div className="text-sm text-gray-300 mb-2">
                <span className="text-gray-400">Device:</span>{' '}
                <span className="text-white">{selected.display_name || selected.id}</span>
              </div>
              <div className="text-sm text-gray-300 mb-3">
                <span className="text-gray-400">Status:</span>{' '}
                <span className={
                  burnerStatus && burnerStatus.current_status === 'Burner Ready'
                    ? 'text-green-400'
                    : burnerStatus && burnerStatus.is_burning
                    ? 'text-yellow-400'
                    : burnerStatus && burnerStatus.last_error
                    ? 'text-red-400'
                    : 'text-gray-300'
                }>
                  {burnerStatus && burnerStatus.current_status ? burnerStatus.current_status : 'Unknown'}
                </span>
              </div>
              <StatusRow label="Disc Present" ok={!!selected.present} />
              <StatusRow label="Writable" ok={!!selected.writable} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

