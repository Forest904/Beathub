// src/pages/SpotifyDownloadPage.js
import React, { useState, useEffect, useRef, useCallback } from 'react'; // <--- Import useCallback
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import DownloadForm from '../components/DownloadForm';
import AlbumGallery from '../components/AlbumGallery';
import ProgressPanel from '../components/ProgressPanel';
import TrackListRich from '../components/TrackListRich';

function SpotifyDownloadPage() {
    const location = useLocation();
    const [albums, setAlbums] = useState([]);
    const [loading, setLoading] = useState(false);
    const [initialFetchComplete, setInitialFetchComplete] = useState(false);
    const [progressVisible, setProgressVisible] = useState(false);
    const [richMetadata, setRichMetadata] = useState(null);
    const [hasActiveDownload, setHasActiveDownload] = useState(false);
    const [selectedAlbumId, setSelectedAlbumId] = useState(null);
    const autoDownloadAttempted = useRef(false);
    const historySectionRef = useRef(null);

    const API_BASE_URL = process.env.NODE_ENV === 'production'
        ? window.location.origin
        : 'http://127.0.0.1:5000';

    // Wrap fetchAlbums with useCallback
    // Its dependency is API_BASE_URL.
    const fetchAlbums = useCallback(async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/albums`);
            setAlbums(response.data);
        } catch (error) {
            console.error('Error fetching albums on initial load:', error);
        } finally {
            setLoading(false);
            setInitialFetchComplete(true);
        }
    }, [API_BASE_URL]);

    // Wrap handleDownload with useCallback
    // Its dependencies are API_BASE_URL and fetchAlbums.
    // fetchAlbums is now stable because it's also wrapped in useCallback.
    const handleDownload = useCallback(async (spotifyLink) => {
        setLoading(true);
        setProgressVisible(true);
        setHasActiveDownload(true);
        setRichMetadata(null);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/download`, { spotify_link: spotifyLink });
            await fetchAlbums(); // Call the stable fetchAlbums
            // Try to fetch rich metadata via spotify_id
            const sid = response.data.spotify_id;
            if (sid) {
                try {
                    const metaResp = await axios.get(`${API_BASE_URL}/api/items/by-spotify/${sid}/metadata`);
                    setRichMetadata(metaResp.data);
                } catch (metaErr) {
                    // Not fatal: metadata might not be persisted yet
                    console.warn('Metadata fetch failed:', metaErr?.response?.data || metaErr?.message);
                }
            }
        } catch (error) {
            console.error('Download error:', error);
        } finally {
            setLoading(false);
        }
    }, [API_BASE_URL, fetchAlbums]); // Add fetchAlbums here

    // Wrap handleDeleteAlbum with useCallback
    // Its dependency is API_BASE_URL.
    // setAlbums and setDownloadMessage are state setters, which are stable by default
    // and don't need to be in the dependency array.
    const handleDeleteAlbum = useCallback(async (albumId) => {
        if (window.confirm('Are you sure you want to delete this album?')) {
            try {
                const response = await axios.delete(`${API_BASE_URL}/api/albums/${albumId}`);
                if (response.data.success) {
                    // Use functional update for state when new state depends on previous state
                    setAlbums(prevAlbums => prevAlbums.filter(album => album.id !== albumId));
                    // If the deleted album was selected, clear selection and details
                    setSelectedAlbumId(prev => (prev === albumId ? null : prev));
                    if (selectedAlbumId === albumId) setRichMetadata(null);
                } else {
                    const data = response.data;
                    console.warn('Failed to delete album:', data.message);
                }
            } catch (error) {
                console.error('Delete album error:', error);
            } finally {
                // no-op
            }
        }
    }, [API_BASE_URL, selectedAlbumId]); // Add API_BASE_URL here

    // Stable callbacks for progress panel (avoid ESLint warnings and reconnections)
    const handleActiveChange = useCallback((active) => {
        setHasActiveDownload(!!active);
    }, [setHasActiveDownload]);

    const handleProgressComplete = useCallback(() => {
        setProgressVisible(false);
        setHasActiveDownload(false);
    }, [setProgressVisible, setHasActiveDownload]);

    // Selecting a previously downloaded album shows its rich metadata
    const handleSelectAlbum = useCallback(async (album) => {
        try {
            setSelectedAlbumId(album.id);
            setRichMetadata(null);
            const metaResp = await axios.get(`${API_BASE_URL}/api/items/${album.id}/metadata`);
            setRichMetadata(metaResp.data);
        } catch (e) {
            console.warn('Failed to fetch selected album metadata:', e?.response?.data || e?.message);
        }
    }, [API_BASE_URL]);

    useEffect(() => {
        // Now fetchAlbums and handleDownload are stable, so they can be safely added to dependencies
        fetchAlbums();

        if (location.state && location.state.spotifyLinkToDownload && !autoDownloadAttempted.current) {
            const linkToDownload = location.state.spotifyLinkToDownload;
            handleDownload(linkToDownload);
            autoDownloadAttempted.current = true;
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [location.state, fetchAlbums, handleDownload]); // <--- Add fetchAlbums and handleDownload here

    // Deselect selected album when clicking outside the history section
    useEffect(() => {
        function handleDocumentClick(e) {
            const node = historySectionRef.current;
            if (node && !node.contains(e.target)) {
                if (selectedAlbumId !== null) {
                    setSelectedAlbumId(null);
                    setRichMetadata(null);
                }
            }
        }
        document.addEventListener('click', handleDocumentClick);
        return () => document.removeEventListener('click', handleDocumentClick);
    }, [selectedAlbumId]);


    return (
        <div className="min-h-screen bg-gray-900 text-white"> {/* Added this wrapper div */}
            <div className="container mx-auto p-4"> {/* Removed redundant text-white and min-h-screen here */}
                <h1 className="text-4xl font-bold text-center mb-8">My Spotify Downloader</h1> {/* text-white already covered by parent */}

                <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
                    <h2 className="text-2xl font-semibold text-white mb-4">Download from Spotify</h2>
                    <DownloadForm onSubmit={handleDownload} loading={loading} />
                    {hasActiveDownload && (
                        <div className="mt-3 flex justify-end">
                            <button
                                type="button"
                                onClick={() => setProgressVisible(v => !v)}
                                className="text-sm px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-gray-200"
                            >
                                {progressVisible ? 'Hide Progress' : 'Show Progress'}
                            </button>
                        </div>
                    )}
                    <ProgressPanel
                        visible={progressVisible}
                        onClose={() => setProgressVisible(false)}
                        baseUrl={API_BASE_URL}
                        onActiveChange={handleActiveChange}
                        onComplete={handleProgressComplete}
                    />
                </div>

                <div ref={historySectionRef} className="bg-gray-800 p-6 rounded-lg shadow-lg">
                    <h2 className="text-2xl font-semibold text-white mb-4">My Previous Downloads:</h2>
                    {loading && !initialFetchComplete ? (
                        <div className="text-center mt-4">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                            <p className="text-gray-300 mt-2">Loading albums...</p>
                        </div>
                    ) : (
                        albums.length === 0 && initialFetchComplete ? (
                            <p className="text-gray-300 text-center">Not one thing in your collection yet. Add some!</p>
                        ) : (
                            <AlbumGallery
                                albums={albums}
                                onDeleteAlbum={handleDeleteAlbum}
                                onAlbumClick={handleSelectAlbum}
                                pageType="history"
                                selectedAlbumId={selectedAlbumId}
                            />
                        )
                    )}
                    {richMetadata && selectedAlbumId && (
                        <div className="mt-6">
                            <h3 className="text-xl font-semibold mb-2">Downloaded Tracks</h3>
                            <TrackListRich tracks={richMetadata.tracks || []} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default SpotifyDownloadPage;
