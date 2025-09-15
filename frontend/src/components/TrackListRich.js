// frontend/src/components/TrackListRich.js
import React from 'react';
import { formatDuration } from '../utils/helpers';

function Badge({ children, color = 'gray' }) {
  const colors = {
    gray: 'bg-gray-700 text-gray-200',
    red: 'bg-red-700 text-white',
    blue: 'bg-blue-700 text-white',
    green: 'bg-green-700 text-white',
    yellow: 'bg-yellow-600 text-black',
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs ${colors[color] || colors.gray}`}>{children}</span>
  );
}

function TrackListRich({ tracks }) {
  if (!tracks || !tracks.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-gray-300">
            <th className="px-2 py-2">#</th>
            <th className="px-2 py-2">Title</th>
            <th className="px-2 py-2">Artists</th>
            <th className="px-2 py-2">Duration</th>
            <th className="px-2 py-2">Explicit</th>
            <th className="px-2 py-2">ISRC</th>
            <th className="px-2 py-2">Disc</th>
            <th className="px-2 py-2">Popularity</th>
          </tr>
        </thead>
        <tbody>
          {tracks.map((t, idx) => (
            <tr key={t.spotify_id || idx} className="border-t border-gray-700">
              <td className="px-2 py-2 text-gray-400">{t.track_number ?? idx + 1}</td>
              <td className="px-2 py-2 text-white">
                <div className="flex items-center gap-2">
                  <span className="truncate max-w-[28ch]" title={t.title}>{t.title}</span>
                  {t.local_lyrics_path && <Badge color="green">Lyrics</Badge>}
                </div>
              </td>
              <td className="px-2 py-2 text-gray-300 truncate max-w-[32ch]" title={(t.artists || []).join(', ')}>
                {(t.artists || []).join(', ')}
              </td>
              <td className="px-2 py-2 text-gray-300">{formatDuration(t.duration_ms)}</td>
              <td className="px-2 py-2">{t.explicit ? <Badge color="red">E</Badge> : <span className="text-gray-500">—</span>}</td>
              <td className="px-2 py-2 text-gray-300 truncate max-w-[18ch]" title={t.isrc || ''}>{t.isrc || '—'}</td>
              <td className="px-2 py-2 text-gray-300">{t.disc_number}{t.disc_count ? `/${t.disc_count}` : ''}</td>
              <td className="px-2 py-2 text-gray-300">{t.popularity ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default TrackListRich;

