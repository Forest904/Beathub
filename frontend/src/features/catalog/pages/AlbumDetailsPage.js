import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import TrackListDiscovery from '../components/TrackListDiscovery.jsx';
import { useAuth } from '../../../shared/hooks/useAuth';
import { endpoints } from '../../../api/client';
import { get } from '../../../api/http';

const FALLBACK_IMAGE = 'https://via.placeholder.com/300x300.png?text=No+Cover';

const AlbumDetailsPage = () => {
  const { albumId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [albumDetails, setAlbumDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copyFeedback, setCopyFeedback] = useState('');
  const isBestOf = String(albumId || '').startsWith('bestof:');

  useEffect(() => {
    if (!albumId) {
      setError('Missing album identifier.');
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadAlbum = async () => {
      try {
        const response = await get(endpoints.albums.details(albumId));
        if (!cancelled) {
          setAlbumDetails(response);
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
    if (isBestOf) {
      navigate('/download', { state: { spotifyLinkToDownload: albumId } });
      return;
    }
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

  const enrichedTracks = useMemo(() => {
    const list = albumDetails?.tracks || [];
    return list.map((t) => ({ ...t, albumId }));
  }, [albumDetails, albumId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-slate-900 dark:text-white">Loading album details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-brandError-600 dark:text-brandError-400">{error}</p>
      </div>
    );
  }

  if (!albumDetails) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-xl text-slate-600 dark:text-gray-400">Album not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
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
            <h1 className="text-4xl font-bold mb-2 text-slate-900 dark:text-white">{albumDetails.title}</h1>
            {isBestOf && (
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-brand-100 text-brand-800 dark:bg-slate-700 dark:text-slate-200 text-xs font-medium mb-2">
                Generated Best-Of • {(albumDetails?.capacity_minutes || 80)}-min CD
              </div>
            )}
            <p className="text-xl text-slate-600 dark:text-gray-400 mb-2">by {albumDetails.artist}</p>
            {!isBestOf && (
              <p className="text-md text-slate-500 dark:text-gray-500 mb-1">Release Date: {releaseDateLabel}</p>
            )}
            <p className="text-md text-slate-500 dark:text-gray-500">Total Tracks: {albumDetails.total_tracks}</p>
            {copyFeedback && <p className="text-brandSuccess-400 mt-4 text-sm">{copyFeedback}</p>}
          </div>

          <div className="w-full md:w-auto md:flex md:items-center">
            <div className="flex flex-col gap-3 md:h-auto">
              {!isBestOf && (
                <button
                  type="button"
                  onClick={() => albumDetails.spotify_url && window.open(albumDetails.spotify_url, '_blank', 'noopener,noreferrer')}
                  className="w-full md:w-auto bg-brandSuccess-600 hover:bg-brandSuccess-700 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
                  disabled={!albumDetails.spotify_url}
                >
                  Listen on Spotify
                </button>
              )}
              {!isBestOf && (
                <button
                  type="button"
                  onClick={handleCopySpotifyLink}
                  className="w-full md:w-auto bg-brand-600 hover:bg-brand-700 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
                >
                  Copy Spotify Link
                </button>
              )}
              {user && (
                <button
                  type="button"
                  onClick={handleDirectDownload}
                  className="w-full md:w-auto bg-brand-700 hover:bg-brand-800 text-white font-semibold py-2 px-4 text-sm rounded-full transition duration-200 md:flex md:items-center md:justify-center"
                >
                  Direct Download
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="mt-12">
          <h2 className="text-3xl font-semibold mb-6 text-center md:text-left text-slate-900 dark:text-white">Tracks</h2>
          {enrichedTracks.length > 0 ? (
            <TrackListDiscovery tracks={enrichedTracks} />
          ) : (
            <p className="text-slate-600 dark:text-gray-500 text-lg">No tracks found for this album.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlbumDetailsPage;
