import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import DownloadForm from '../components/DownloadForm';
import CancelDownloadButton from '../components/CancelDownloadButton';
import DownloadProgress from '../components/DownloadProgress';
import LyricsPanel from '../components/LyricsPanel';
import useDownloadHistory from '../hooks/useDownloadHistory';
import AlbumGallery from '../../../shared/components/AlbumGallery';
import TrackListRich from '../../../shared/components/TrackListRich';
import { AlbumCardVariant } from '../../../shared/components/AlbumCard';
import Message from '../../../shared/components/Message';
import { usePlayer } from '../../../player/PlayerContext';
import { useAuth } from '../../../shared/hooks/useAuth';
import { API_BASE_URL, endpoints } from '../../../api/client';
import { get, post } from '../../../api/http';

const extractSpotifyId = (link) => {
  if (!link) return null;
  const trimmed = String(link).trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('spotify:')) {
    const parts = trimmed.split(':');
    return parts[parts.length - 1] || null;
  }
  try {
    const candidate = trimmed.startsWith('http') ? trimmed : `https://${trimmed}`;
    const parsed = new URL(candidate);
    const segments = parsed.pathname.split('/').filter(Boolean);
    if (segments.length >= 2) {
      return segments[1] || null;
    }
    if (segments.length === 1) {
      return segments[0] || null;
    }
  } catch (error) {
    return null;
  }
  return null;
};

const normalizeSpotifyUrl = (link) => {
  if (!link) return null;
  const trimmed = String(link).trim();
  if (!trimmed) return null;
  if (trimmed.startsWith('spotify:')) {
    return trimmed.toLowerCase();
  }
  try {
    const candidate = trimmed.startsWith('http') ? trimmed : `https://${trimmed}`;
    const parsed = new URL(candidate);
    parsed.search = '';
    parsed.hash = '';
    const normalized = `${parsed.origin}${parsed.pathname}`.replace(/\/$/, '');
    return normalized.toLowerCase();
  } catch (error) {
    return trimmed.toLowerCase();
  }
};

const AUTO_REFRESH_RETRY_LIMIT = 4;
const AUTO_REFRESH_DELAY_MS = 1400;

const SpotifyDownloadPage = () => {
  const location = useLocation();
  const player = usePlayer();
  const { user } = useAuth();
  const {
    items: albums,
    loading: historyLoading,
    refresh: refreshHistory,
    remove: removeAlbum,
  } = useDownloadHistory();
  const [loading, setLoading] = useState(false);
  const [initialFetchComplete, setInitialFetchComplete] = useState(false);
  const [progressVisible, setProgressVisible] = useState(false);
  const [richMetadata, setRichMetadata] = useState(null);
  const [hasActiveDownload, setHasActiveDownload] = useState(false);
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeLink, setActiveLink] = useState(null);
  const [cancelRequested, setCancelRequested] = useState(false);
  const [selectedAlbumId, setSelectedAlbumId] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [pendingSelection, setPendingSelection] = useState(null);
  const [lyricsVisible, setLyricsVisible] = useState(false);
  const [lyricsTrack, setLyricsTrack] = useState(null);
  const autoDownloadAttempted = useRef(false);
  const historySectionRef = useRef(null);

  const apiBaseUrl = API_BASE_URL;

  const fetchAlbums = useCallback(async (options = {}) => {
    const { silent = false } = options;
    try {
      await refreshHistory({ silent });
      if (!silent) {
        setErrorMessage(null);
      }
    } catch (error) {
      console.error('Error fetching albums', error);
      if (!silent) {
        if (error?.response?.status === 401 || error?.response?.status === 403) {
          setErrorMessage('Please sign in to view your downloaded items.');
        } else {
          setErrorMessage('We could not load your downloads just now. Please try again.');
        }
      }
    } finally {
      setInitialFetchComplete(true);
    }
  }, [refreshHistory]);

  const handleDownload = useCallback(
    async (spotifyLink) => {
      setLoading(true);
      setProgressVisible(true);
      setHasActiveDownload(true);
      setActiveLink(spotifyLink);
      setCancelRequested(false);
      setRichMetadata(null);
      setErrorMessage(null);

      try {
        // Start async job so it can be cancelled; backend returns 202 with job_id
        const data = await post(endpoints.downloads.start(), { spotify_link: spotifyLink, async: true });
        if (data && data.job_id) {
          setActiveJobId(data.job_id);
        }
      } catch (error) {
        console.error('Download error', error);
        setErrorMessage('We could not start that download. Please check the link and retry.');
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const handleDeleteAlbum = useCallback(
    async (albumId) => {
      const confirmed = window.confirm('Are you sure you want to delete this album?');
      if (!confirmed) {
        return;
      }

      try {
        const success = await removeAlbum(albumId);
        if (success) {
          setSelectedAlbumId((prev) => (prev === albumId ? null : prev));
          if (selectedAlbumId === albumId) {
            setRichMetadata(null);
          }
          setErrorMessage(null);
        } else {
          setErrorMessage('Failed to delete album.');
        }
      } catch (error) {
        console.error('Delete album error', error);
        if (error?.response?.status === 403) {
          setErrorMessage('You can only delete downloads from your own account.');
        } else {
          setErrorMessage('We could not delete that album. Please try again.');
        }
      }
    },
    [removeAlbum, selectedAlbumId],
  );

  const handleActiveChange = useCallback((active) => {
    setHasActiveDownload(Boolean(active));
  }, []);

  // Ensure progress panel becomes visible whenever an active download starts
  useEffect(() => {
    if (hasActiveDownload) setProgressVisible(true);
  }, [hasActiveDownload]);

  const handleProgressComplete = useCallback((completionPayload) => {
    const normalizedStatus = (() => {
      if (completionPayload && typeof completionPayload === 'object' && completionPayload.status) {
        try {
          return String(completionPayload.status).toLowerCase();
        } catch (error) {
          return null;
        }
      }
      return null;
    })();

    const candidateResult =
      completionPayload && typeof completionPayload === 'object' && completionPayload.result && typeof completionPayload.result === 'object'
        ? completionPayload.result
        : completionPayload && typeof completionPayload === 'object' && completionPayload.status === 'success'
          ? completionPayload
          : null;

    const resultStatus = candidateResult && typeof candidateResult.status === 'string'
      ? candidateResult.status.toLowerCase()
      : null;

    const succeeded =
      (normalizedStatus && (normalizedStatus === 'complete' || normalizedStatus === 'completed' || normalizedStatus === 'success')) ||
      (resultStatus === 'success');

    const resultSpotifyId =
      succeeded && candidateResult && typeof candidateResult.spotify_id === 'string' ? candidateResult.spotify_id : null;
    const resultSpotifyUrl =
      succeeded && candidateResult && typeof candidateResult.spotify_url === 'string' ? candidateResult.spotify_url : null;
    const derivedSpotifyId = succeeded ? (resultSpotifyId || extractSpotifyId(activeLink)) : null;
    const derivedSpotifyUrl = succeeded ? (resultSpotifyUrl || activeLink || null) : null;

    if (succeeded && (derivedSpotifyId || derivedSpotifyUrl)) {
      setPendingSelection({
        spotifyId: derivedSpotifyId || null,
        spotifyUrl: derivedSpotifyUrl || null,
        retriesRemaining: AUTO_REFRESH_RETRY_LIMIT,
        token: Date.now(),
      });
    } else {
      setPendingSelection(null);
    }

    setProgressVisible(false);
    setHasActiveDownload(false);
    setActiveJobId(null);
    setActiveLink(null);
    setCancelRequested(false);
    fetchAlbums({ silent: true });
  }, [activeLink, fetchAlbums]);

  const handleProgressCancelled = useCallback(() => {
    setProgressVisible(false);
    setHasActiveDownload(false);
    setActiveJobId(null);
    setActiveLink(null);
    setCancelRequested(false);
  }, []);

  const handleCancelClick = useCallback(async () => {
    if (!activeJobId && !activeLink) return;
    try {
      const payload = activeJobId ? { job_id: activeJobId } : { link: activeLink };
      await post(endpoints.downloads.cancel(), payload);
      setCancelRequested(true);
    } catch (e) {
      // Keep UX simple; allow polling/SSE to reconcile final state
    }
  }, [activeJobId, activeLink]);

  // Poll job status while an async job is active, so UI stays accurate even if SSE drops
  useEffect(() => {
    if (!activeJobId) return undefined;
    let cancelled = false;
    const tick = async () => {
      try {
        const res = await get(endpoints.downloads.job(activeJobId));
        if (cancelled) return;
        const st = (res && res.status) || 'pending';
        if (st === 'completed') {
          handleProgressComplete(res);
          return;
        }
        if (st === 'failed' || st === 'cancelled') {
          if (st === 'cancelled') {
            handleProgressCancelled();
          } else {
            setErrorMessage(res && res.error ? String(res.error) : 'Download failed.');
            handleProgressComplete(res);
          }
          return;
        }
      } catch (e) {
        // Keep polling; transient errors are expected if server restarts
      }
    };
    const iv = setInterval(tick, 3000);
    // fire immediate check
    tick();
    return () => {
      clearInterval(iv);
      cancelled = true;
    };
  }, [activeJobId, handleProgressCancelled, handleProgressComplete]);

  const handleSelectAlbum = useCallback(
    async (album, options = {}) => {
      if (!album) return;
      const force = Boolean(options.force);
      const isSame = selectedAlbumId === album.id;
      if (isSame && !force) {
        // Toggle off when clicking the already-selected card
        setSelectedAlbumId(null);
        setRichMetadata(null);
        return;
      }
      if (!isSame) {
        setSelectedAlbumId(album.id);
      }
      setRichMetadata(null);
      try {
        const metadataResponse = await get(endpoints.items.metadata(album.id));
        setRichMetadata(metadataResponse);
      } catch (error) {
        console.warn('Failed to fetch selected album metadata', error);
      }
    },
    [selectedAlbumId],
  );

  useEffect(() => {
    if (!user) return;
    fetchAlbums();
  }, [fetchAlbums, user]);

  // If instructed, show the progress panel immediately (e.g., from compilation sidebar)
  useEffect(() => {
    if (location.state && location.state.showProgressPanel) {
      setProgressVisible(true);
    }
  }, [location.state]);

  useEffect(() => {
    if (!pendingSelection) return undefined;
    const { spotifyId, spotifyUrl, retriesRemaining = 0, token } = pendingSelection;
    if (!spotifyId && !spotifyUrl) {
      setPendingSelection(null);
      return undefined;
    }

    const scheduleRefreshAttempt = () => {
      if (retriesRemaining <= 0) {
        setPendingSelection(null);
        return undefined;
      }
      const timer = setTimeout(() => {
        fetchAlbums({ silent: true });
        setPendingSelection((prev) => {
          if (!prev || prev.token !== token) {
            return prev;
          }
          const nextRetries = prev.retriesRemaining > 0 ? prev.retriesRemaining - 1 : 0;
          return nextRetries > 0 ? { ...prev, retriesRemaining: nextRetries } : null;
        });
      }, AUTO_REFRESH_DELAY_MS);
      return timer;
    };

    if (!albums || albums.length === 0) {
      const pendingTimer = scheduleRefreshAttempt();
      return () => {
        if (pendingTimer) {
          clearTimeout(pendingTimer);
        }
      };
    }

    const normalizedTargetUrl = normalizeSpotifyUrl(spotifyUrl);
    const match = albums.find((album) => {
      if (spotifyId && album.spotify_id === spotifyId) {
        return true;
      }
      if (normalizedTargetUrl && normalizeSpotifyUrl(album.spotify_url) === normalizedTargetUrl) {
        return true;
      }
      return false;
    });
    if (match) {
      const alreadySelected = selectedAlbumId === match.id;
      handleSelectAlbum(match, { force: alreadySelected });
      setPendingSelection(null);
      if (historySectionRef.current && typeof historySectionRef.current.scrollIntoView === 'function') {
        try {
          historySectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (err) {
          historySectionRef.current.scrollIntoView();
        }
      }
      return undefined;
    }

    const retryTimer = scheduleRefreshAttempt();
    return () => {
      if (retryTimer) {
        clearTimeout(retryTimer);
      }
    };
  }, [albums, pendingSelection, selectedAlbumId, handleSelectAlbum, fetchAlbums]);

  // If a spotify id to select is provided, select matching item when albums list loads
  useEffect(() => {
    const target = location.state && location.state.selectSpotifyId;
    if (!target || albums.length === 0) return;
    const match = albums.find((a) => a.spotify_id === target);
    if (match) {
      setSelectedAlbumId(match.id);
    }
  }, [albums, location.state]);

  useEffect(() => {
    if (!user) return;
    if (!location.state?.spotifyLinkToDownload || autoDownloadAttempted.current) {
      return;
    }

    handleDownload(location.state.spotifyLinkToDownload);
    autoDownloadAttempted.current = true;
    window.history.replaceState({}, document.title, window.location.pathname);
  }, [handleDownload, location.state, user]);

  useEffect(() => {
    const handleDocumentClick = (event) => {
      // Keep album selection when lyrics panel is open
      if (lyricsVisible) return;
      // Ignore clicks within the PlayerBar so selection doesn't clear
      const playerBar = document.getElementById('player-bar-root');
      if (playerBar && playerBar.contains(event.target)) return;
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

  const buildAudioUrl = useCallback((track) => {
    if (!track || !selectedAlbumId) return null;
    const primaryArtist = Array.isArray(track.artists) && track.artists.length > 0 ? track.artists[0] : '';
    const params = new URLSearchParams({ title: track.title || '', artist: primaryArtist || '' });
    return `${apiBaseUrl}/api/items/${selectedAlbumId}/audio?${params.toString()}`;
  }, [apiBaseUrl, selectedAlbumId]);

  const handlePlayTrack = useCallback((track, index) => {
    if (!player || !sortedTracks || sortedTracks.length === 0) return;
    const queue = sortedTracks.map((t) => ({
      title: t.title,
      artists: t.artists || [],
      audioUrl: buildAudioUrl(t),
      albumId: selectedAlbumId,
      // preserve minimal data for lyrics panel
      artist: Array.isArray(t.artists) && t.artists.length > 0 ? t.artists[0] : '',
    }));
    player.playQueue(queue, index);
  }, [player, sortedTracks, buildAudioUrl, selectedAlbumId]);

  return (
    <div className="min-h-screen">
      { !user ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-3 text-slate-900 dark:text-white">Sign in to download</h1>
            <p className="text-slate-600 dark:text-slate-300 mb-4">Please log in to access the download feature and your history.</p>
            <Link to="/login" className="inline-block rounded-full bg-brand-600 px-4 py-2 text-white hover:bg-brand-700 dark:bg-brandDark-500 dark:hover:bg-brandDark-400">Go to Login</Link>
          </div>
        </div>
      ) : (
      <>
      <div className="container mx-auto p-4">
        <h1 className="text-4xl font-bold text-center mb-8 text-slate-900 dark:text-white">My Spotify Downloader</h1>

        <div className="bg-brand-50 dark:bg-gray-800 p-6 rounded-lg shadow-lg mb-8 ring-1 ring-brand-100 dark:ring-0">
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">Download from Spotify</h2>
          <DownloadForm
            onSubmit={handleDownload}
            loading={loading}
            middleAction={
              hasActiveDownload ? (
                <CancelDownloadButton onCancel={handleCancelClick} disabled={cancelRequested} />
              ) : null
            }
            rightAction={
              hasActiveDownload || progressVisible ? (
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
            onCancelled={handleProgressCancelled}
            jobId={activeJobId || undefined}
            link={activeLink || undefined}
          />
        </div>

        <div ref={historySectionRef} className="bg-brand-50 dark:bg-gray-800 p-6 rounded-lg shadow-lg ring-1 ring-brand-100 dark:ring-0">
          <h2 className="text-2xl font-semibold text-slate-900 dark:text-white mb-4">My Previous Downloads</h2>
          {historyLoading && !initialFetchComplete ? (
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
                enablePlay
                onPlayTrack={handlePlayTrack}
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
      </>
      )}
    </div>
  );
};

export default SpotifyDownloadPage;