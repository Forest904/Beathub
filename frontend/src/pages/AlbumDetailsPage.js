import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { formatDuration } from '../utils/helpers';

const FALLBACK_IMAGE = 'https://via.placeholder.com/300x300.png?text=No+Cover';

const AlbumDetailsPage = () => {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const [albumDetails, setAlbumDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copyFeedback, setCopyFeedback] = useState('');

  useEffect(() => {
    if (!albumId) {
      setError('Missing album identifier.');
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadAlbum = async () => {
      try {
        const response = await axios.get(`/api/album_details/${albumId}`);
        if (!cancelled) {
          setAlbumDetails(response.data);
          setError(null);
        }
      } catch (requestError) {
        console.error('Failed to fetch album details', requestError);
        if (!cancelled) {
          setError('Failed to load album details. Please try again.');
          setAlbumDetails(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadAlbum();

    return () => {
      cancelled = true;
    };
  }, [albumId]);

  useEffect(() => {
    if (!copyFeedback) {
      return undefined;
    }
    const timer = setTimeout(() => setCopyFeedback(''), 2000);
    return () => clearTimeout(timer);
  }, [copyFeedback]);

  const handleCopySpotifyLink = async () => {
    if (!albumDetails?.spotify_url) {
      setCopyFeedback('Spotify link unavailable.');
      return;
    }
    try {
      await navigator.clipboard.writeText(albumDetails.spotify_url);
      setCopyFeedback('Link copied!');
    } catch (copyError) {
      console.error('Failed to copy spotify link', copyError);
      setCopyFeedback('Failed to copy link.');
    }
  };

  const handleDirectDownload = () => {
    if (!albumDetails?.spotify_url) {
      setCopyFeedback('Spotify link unavailable.');
      return;
    }
    navigate('/download', { state: { spotifyLinkToDownload: albumDetails.spotify_url } });
  };

  const releaseDateLabel = useMemo(() => {
    if (!albumDetails?.release_date) {
      return 'N/A';
    }
    return new Date(albumDetails.release_date).toLocaleDateString();
  }, [albumDetails]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-xl">Loading album details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-xl text-red-400">{error}</p>
      </div>
    );
  }

  if (!albumDetails) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-xl text-gray-400">Album not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto p-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between space-y-6 md:space-y-0 md:space-x-8">
          <div className="w-full md:w-1/6 lg:w-1/6 max-w-xs md:max-w-sm md:flex md:items-center">
            <div className="relative w-full aspect-square overflow-hidden rounded-lg shadow-xl">
              <img
                src={albumDetails.image_url || FALLBACK_IMAGE}
                alt={`${albumDetails.title} Album Cover`}
                className="absolute inset-0 w-full h-full object-cover"
              />
            </div>
          </div>

          <div className="w-full md:flex-1 md:mx-8 flex flex-col justify-center text-center md:text-center md:items-center">
            <h1 className="text-4xl font-bold mb-2">{albumDetails.title}</h1>
            <p className="text-xl text-gray-400 mb-2">by {albumDetails.artist}</p>
            <p className="text-md text-gray-500 mb-1">Release Date: {releaseDateLabel}</p>
            <p className="text-md text-gray-500">Total Tracks: {albumDetails.total_tracks}</p>
            {copyFeedback && <p className="text-green-400 mt-4 text-sm">{copyFeedback}</p>}
          </div>

          <div className="w-full md:w-auto md:flex md:items-center">
            <div className="flex flex-col gap-3 md:h-auto">
              <button
                type="button"
                onClick={() => albumDetails.spotify_url && window.open(albumDetails.spotify_url, '_blank', 'noopener,noreferrer')}
                className="w-full md:w-auto bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
                disabled={!albumDetails.spotify_url}
              >
                Listen on Spotify
              </button>
              <button
                type="button"
                onClick={handleCopySpotifyLink}
                className="w-full md:w-auto bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
              >
                Copy Spotify Link
              </button>
              <button
                type="button"
                onClick={handleDirectDownload}
                className="w-full md:w-auto bg-indigo-500 hover:bg-indigo-600 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
              >
                Direct Download
              </button>
            </div>
          </div>
        </div>

        <div className="mt-12">
          <h2 className="text-3xl font-semibold mb-6 text-center md:text-left">Tracks</h2>
          {albumDetails.tracks?.length ? (
            <ul className="space-y-2">
              {albumDetails.tracks.map((track, index) => (
                <li
                  key={track.spotify_id || index}
                  className="bg-gray-800 p-4 rounded-lg shadow flex flex-col sm:flex-row justify-between items-center"
                >
                  <div className="flex-1 text-left mb-2 sm:mb-0">
                    <p className="text-lg font-medium">{track.track_number}. {track.title}</p>
                    <p className="text-sm text-gray-400">{(track.artists || []).join(', ')}</p>
                  </div>
                  <p className="text-gray-400 text-sm">{formatDuration(track.duration_ms)}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-lg">No tracks found for this album.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlbumDetailsPage;
