// frontend/src/components/DeviceGrid.js
import React from 'react';

function StatusPill({ ok, label }) {
  const cls = ok ? 'bg-green-700 text-green-100' : 'bg-gray-700 text-gray-300';
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${cls} mr-2`}>{label}</span>
  );
}

export default function DeviceGrid({ devices, onSelect }) {
  if (!devices || devices.length === 0) {
    return (
      <div className="text-gray-400">No connected burner detected.</div>
    );
  }

  // Common case: single device — make it full width but keep grid responsive
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {devices.map((d) => (
        <div key={d.id} className="border border-gray-700 rounded p-4 bg-gray-800">
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="font-semibold text-white">{d.display_name || d.id}</div>
              <div className="text-xs text-gray-400">{d.id}</div>
            </div>
            {d.active ? (
              <span className="text-yellow-400 text-sm font-semibold">Active</span>
            ) : d.selected ? (
              <span className="text-blue-400 text-sm font-semibold">Selected</span>
            ) : (
              <button
                className="text-sm bg-blue-700 hover:bg-blue-800 text-white px-3 py-1 rounded"
                onClick={() => onSelect && onSelect(d)}
              >
                Select
              </button>
            )}
          </div>
          <div className="mb-2">
            <StatusPill ok={!!d.present} label={d.present ? 'Disc Present' : 'No Disc'} />
            <StatusPill ok={!!d.writable} label={d.writable ? 'Writable' : 'Not Writable'} />
          </div>
          {d.volume_paths && d.volume_paths.length > 0 && (
            <div className="text-xs text-gray-400">{d.volume_paths.join(' · ')}</div>
          )}
        </div>
      ))}
    </div>
  );
}
