import React, { useState } from 'react';
import PropTypes from 'prop-types';

const DownloadForm = ({ onSubmit, loading, middleAction, rightAction }) => {
  const [spotifyLink, setSpotifyLink] = useState('');

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmedLink = spotifyLink.trim();
    if (!trimmedLink) {
      return;
    }

    onSubmit(trimmedLink);
    setSpotifyLink('');
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="spotifyLink" className="block text-left text-sm font-medium mb-2 text-brand-800 dark:text-gray-300">
          Spotify Link (Track, Album, or Playlist)
        </label>
        <input
          type="url"
          id="spotifyLink"
          value={spotifyLink}
          onChange={(event) => setSpotifyLink(event.target.value)}
          placeholder="https://open.spotify.com/album/..."
          required
          className="w-full px-4 py-2 bg-white text-slate-900 border border-brand-300 rounded-md focus:ring focus:ring-brand-500 focus:border-brand-500 focus:outline-none dark:bg-gray-600 dark:text-gray-100 dark:border-gray-500"
          disabled={loading}
        />
      </div>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          className="flex-1 flex items-center justify-center bg-brand-600 hover:bg-brand-700 text-white font-semibold py-2 px-4 rounded-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loading || !spotifyLink.trim()}
        >
          {loading ? (
            <>
              <span className="w-5 h-5 border-2 border-white border-t-brand-500 dark:border-t-brandDark-400 rounded-full animate-spin mr-2" />
              Downloading...
            </>
          ) : (
            'Download'
          )}
        </button>
        {middleAction}
        {rightAction}
      </div>
    </form>
  );
};

DownloadForm.propTypes = {
  onSubmit: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  middleAction: PropTypes.node,
  rightAction: PropTypes.node,
};

DownloadForm.defaultProps = {
  loading: false,
  middleAction: null,
  rightAction: null,
};

export default DownloadForm;
