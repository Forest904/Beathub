import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import DownloadForm from '../components/DownloadForm';
import AlbumGallery from '../components/AlbumGallery';
import DownloadProgress from '../components/DownloadProgress';
import TrackListRich from '../components/TrackListRich';
import { AlbumCardVariant } from '../components/AlbumCard';
import Message from '../components/Message';
import LyricsPanel from '../components/LyricsPanel';

const SpotifyDownloadPage = () => {
  const location = useLocation();
  const [albums, setAlbums] = useState([]);
  const [loading, setLoading] = useState(false);
  const [initialFetchComplete, setInitialFetchComplete] = useState(false);
  const [progressVisible, setProgressVisible] = useState(false);
  const [richMetadata, setRichMetadata] = useState(null);
  const [hasActiveDownload, setHasActiveDownload] = useState(false);
  const [selectedAlbumId, setSelectedAlbumId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [lyricsVisible, setLyricsVisible] = useState(false);
  const [lyricsTrack, setLyricsTrack] = useState(null);
  const autoDownloadAttempted = useRef(false);
  const historySectionRef = useRef(null);

  const apiBaseUrl =
    process.env.NODE_ENV === 'production' ? window.location.origin : 'http://127.0.0.1:5000';

  const fetchAlbums = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${apiBaseUrl}/api/albums`);
      setAlbums(response.data);
      setErrorMessage(null);
    } catch (error) {
      console.error('Error fetching albums', error);
      setErrorMessage('We could not load your downloads just now. Please try again.');
    } finally {
      setLoading(false);
      setInitialFetchComplete(true);
    }
  }, [apiBaseUrl]);

  const handleDownload = useCallback(
    async (spotifyLink) => {
      setLoading(true);
      setProgressVisible(true);
      setHasActiveDownload(true);
      setRichMetadata(null);
      setErrorMessage(null);

      try {
        const response = await axios.post(`${apiBaseUrl}/api/download`, { spotify_link: spotifyLink });
        await fetchAlbums();
        const spotifyId = response.data.spotify_id;
        if (spotifyId) {
          try {
            const metadataResponse = await axios.get(
              `${apiBaseUrl}/api/items/by-spotify/${spotifyId}/metadata`,
            );
            setRichMetadata(metadataResponse.data);
          } catch (metadataError) {
            console.warn('Metadata fetch failed', metadataError);
          }
        }
      } catch (error) {
        console.error('Download error', error);
        setErrorMessage('We could not start that download. Please check the link and retry.');
      } finally {
        setLoading(false);
      }
    },
    [apiBaseUrl, fetchAlbums],
  );

  const handleDeleteAlbum = useCallback(
    async (albumId) => {
      const confirmed = window.confirm('Are you sure you want to delete this album?');
      if (!confirmed) {
        return;
      }

      try {
        const response = await axios.delete(`${apiBaseUrl}/api/albums/${albumId}`);
        if (response.data.success) {
          setAlbums((prev) => prev.filter((album) => album.id !== albumId));
          setSelectedAlbumId((prev) => (prev === albumId ? null : prev));
          if (selectedAlbumId === albumId) {
            setRichMetadata(null);
          }
        } else {
          setErrorMessage(response.data.message || 'Failed to delete album.');
        }
      } catch (error) {
        console.error('Delete album error', error);
        setErrorMessage('We could not delete that album. Please try again.');
      }
    },
    [apiBaseUrl, selectedAlbumId],
  );

  const handleActiveChange = useCallback((active) => {
    setHasActiveDownload(Boolean(active));
  }, []);

  const handleProgressComplete = useCallback(() => {
    setProgressVisible(false);
    setHasActiveDownload(false);
    fetchAlbums();
  }, [fetchAlbums]);

  const handleSelectAlbum = useCallback(
    async (album) => {
      setSelectedAlbumId(album.id);
      setRichMetadata(null);
      try {
        const metadataResponse = await axios.get(`${apiBaseUrl}/api/items/${album.id}/metadata`);
        setRichMetadata(metadataResponse.data);
      } catch (error) {
        console.warn('Failed to fetch selected album metadata', error);
      }
    },
    [apiBaseUrl],
  );

  useEffect(() => {
    fetchAlbums();
  }, [fetchAlbums]);

  useEffect(() => {
    if (!location.state?.spotifyLinkToDownload || autoDownloadAttempted.current) {
      return;
    }

    handleDownload(location.state.spotifyLinkToDownload);
    autoDownloadAttempted.current = true;
    window.history.replaceState({}, document.title, window.location.pathname);
  }, [handleDownload, location.state]);

  useEffect(() => {
    const handleDocumentClick = (event) => {
      // Keep album selection when lyrics panel is open
      if (lyricsVisible) return;
      const node = historySectionRef.current;
      if (!node || node.contains(event.target)) {
        return;
      }
      if (selectedAlbumId !== null) {
        setSelectedAlbumId(null);
        setRichMetadata(null);
      }
    };

    document.addEventListener('click', handleDocumentClick);
    return () => document.removeEventListener('click', handleDocumentClick);
  }, [selectedAlbumId, lyricsVisible]);

  const sortedTracks = useMemo(() => {
    const tracks = richMetadata?.tracks || [];
    return [...tracks].sort((a, b) => {
      const ad = Number(a?.disc_number ?? 1);
      const bd = Number(b?.disc_number ?? 1);
      if (Number.isFinite(ad) && Number.isFinite(bd) && ad !== bd) return ad - bd;
      const at = Number(a?.track_number ?? 0);
      const bt = Number(b?.track_number ?? 0);
      if (Number.isFinite(at) && Number.isFinite(bt) && at !== bt) return at - bt;
      return 0;
    });
  }, [richMetadata?.tracks]);

  const hasMultipleDiscs = useMemo(() => {
    const discs = new Set((sortedTracks || []).map((t) => Number(t?.disc_number ?? 1)));
    return discs.size > 1;
  }, [sortedTracks]);

  const handleLyricsClick = useCallback((track) => {
    setLyricsTrack(track || null);
    setLyricsVisible(true);
  }, []);

  return (
    <div className="min-h-screen">
      <div className="container mx-auto p-4">
        <h1 className="text-4xl font-bold text-center mb-8 text-slate-900 dark:text-white">My Spotify Downloader</h1>

        <div className="bg-brand-50 dark:bg-gray-800 p-6 rounded-lg shadow-lg mb-8 ring-1 ring-brand-100 dark:ring-0">
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">Download from Spotify</h2>
          <DownloadForm
            onSubmit={handleDownload}
            loading={loading}
            rightAction={
              hasActiveDownload ? (
                <button
                  type="button"
                  onClick={() => setProgressVisible((prev) => !prev)}
                  className="text-sm px-3 py-2 rounded-md bg-slate-200 hover:bg-slate-300 text-slate-700 whitespace-nowrap dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200"
                >
                  {progressVisible ? 'Hide Panel' : 'Show Panel'}
                </button>
              ) : null
            }
          />
          {errorMessage && <Message type="error" text={errorMessage} />}
          <DownloadProgress
            visible={progressVisible}
            onClose={() => setProgressVisible(false)}
            baseUrl={apiBaseUrl}
            onActiveChange={handleActiveChange}
            onComplete={handleProgressComplete}
          />
        </div>

        <div ref={historySectionRef} className="bg-brand-50 dark:bg-gray-800 p-6 rounded-lg shadow-lg ring-1 ring-brand-100 dark:ring-0">
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">My Previous Downloads</h2>
          {loading && !initialFetchComplete ? (
            <div className="text-center mt-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-600 dark:border-brandDark-500 mx-auto" />
              <p className="text-slate-600 dark:text-gray-300 mt-2">Loading albums...</p>
            </div>
          ) : albums.length === 0 && initialFetchComplete ? (
            <p className="text-slate-600 dark:text-gray-300 text-center">No downloads yet. Add some!</p>
          ) : (
            <AlbumGallery
              albums={albums}
              onDelete={handleDeleteAlbum}
              onSelect={handleSelectAlbum}
              variant={AlbumCardVariant.HISTORY}
              selectedAlbumId={selectedAlbumId}
            />
          )}
          {richMetadata && selectedAlbumId && (
            <div className="mt-6">
              {(() => {
                const albumTitle =
                  (richMetadata && (richMetadata.name || (richMetadata.album && richMetadata.album.name) || richMetadata.title)) ||
                  'Downloaded Tracks';
                return <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-white">{albumTitle}</h3>;
              })()}
              <TrackListRich
                tracks={sortedTracks}
                showDiscHeaders={hasMultipleDiscs}
                showIsrc={false}
                showDisc={false}
                showPopularity={false}
                onLyricsClick={handleLyricsClick}
              />
            </div>
          )}
        </div>
      </div>
      <LyricsPanel
        visible={lyricsVisible}
        onClose={() => setLyricsVisible(false)}
        baseUrl={apiBaseUrl}
        albumId={selectedAlbumId}
        track={lyricsTrack}
      />
    </div>
  );
};

export default SpotifyDownloadPage;
