// src/components/DownloadForm.js
import React, { useState } from 'react';

function DownloadForm({ onSubmit, loading }) {
    const [spotifyLink, setSpotifyLink] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        // Only submit if there's a link to prevent empty submissions
        if (spotifyLink.trim()) {
            onSubmit(spotifyLink);
            setSpotifyLink(''); // Clear input after submission
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label htmlFor="spotifyLink" className="block text-left text-sm font-medium mb-2 text-gray-300">
                    Spotify Link (Track, Album, or Playlist):
                </label>
                <input
                    type="url"
                    id="spotifyLink"
                    value={spotifyLink}
                    onChange={(e) => setSpotifyLink(e.target.value)}
                    placeholder="e.g., https://open.spotify.com/album/..."
                    required
                    // These classes maintain your dark input field style
                    className="input-field w-full px-4 py-2 bg-gray-600 text-gray-100 border border-gray-500 rounded-md
                               focus:ring focus:ring-blue-400 focus:border-blue-400 focus:outline-none" // Added focus:outline-none for better consistency
                    disabled={loading}
                />
            </div>
            <button
                type="submit"
                className="btn w-full flex items-center justify-center bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md
                           transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed" // Added disabled styles for clarity
                disabled={loading || !spotifyLink.trim()} // Disable if loading or input is empty
            >
                {loading ? (
                    <>
                        <span className="loading-spinner w-5 h-5 border-2 border-white border-t-blue-400 rounded-full animate-spin mr-2"></span>
                        Downloading...
                    </>
                ) : (
                    'Download'
                )}
            </button>
        </form>
    );
}

export default DownloadForm;