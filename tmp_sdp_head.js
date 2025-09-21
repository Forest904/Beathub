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
import { usePlayer } from '../player/PlayerContext';

const SpotifyDownloadPage = () => {
  const location = useLocation();
  const player = usePlayer();
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

  // Ensure progress panel becomes visible whenever an active download starts
  useEffect(() => {
    if (hasActiveDownload) setProgressVisible(true);
  }, [hasActiveDownload]);

  const handleProgressComplete = useCallback(() => {
    setProgressVisible(false);
    setHasActiveDownload(false);
    fetchAlbums();
  }, [fetchAlbums]);

  const handleSelectAlbum = useCallback(
  async (album) => {
    if (!album) return;
    const isSame = selectedAlbumId === album.id;
    if (isSame) {
      // Toggle off when clicking the already-selected card
      setSelectedAlbumId(null);
      setRichMetadata(null);
      return;
    }
    setSelectedAlbumId(album.id);
    setRichMetadata(null);
    try {
      const metadataResponse = await axios.get(`${apiBaseUrl}/api/items/${album.id}/metadata`);
      setRichMetadata(metadataResponse.data);
    } catch (error) {
      console.warn('Failed to fetch selected album metadata', error);
    }
  },
  [apiBaseUrl, selectedAlbumId],
);
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

  // If instructed, show the progress panel immediately (e.g., from compilation sidebar)
  useEffect(() => {
    if (location.state && location.state.showProgressPanel) {
      setProgressVisible(true);
    }
  }, [location.state]);

  // If a spotify id to select is provided, select matching item when albums list loads
  useEffect(() => {
    const target = location.state && location.state.selectSpotifyId;
    if (!target || albums.length === 0) return;
    const match = albums.find((a) => a.spotify_id === target);
    if (match) {
      setSelectedAlbumId(match.id);
    }
