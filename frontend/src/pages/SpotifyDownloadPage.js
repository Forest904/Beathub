// src/pages/SpotifyDownloadPage.js
import React, { useState, useEffect, useRef, useCallback } from 'react'; // <--- Import useCallback
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import DownloadForm from '../components/DownloadForm';
import AlbumGallery from '../components/AlbumGallery';
import Message from '../components/Message';

function SpotifyDownloadPage() {
    const location = useLocation();
    const [downloadMessage, setDownloadMessage] = useState(null);
    const [albums, setAlbums] = useState([]);
    const [loading, setLoading] = useState(false);
    const [jobProgress, setJobProgress] = useState(null);
    const [statusText, setStatusText] = useState('');
    const [initialFetchComplete, setInitialFetchComplete] = useState(false);
    const autoDownloadAttempted = useRef(false);
    const eventSourceRef = useRef(null);

    const API_BASE_URL = process.env.NODE_ENV === 'production'
        ? window.location.origin
        : 'http://localhost:5000';

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
        setDownloadMessage({ type: 'info', text: "Initiating download..." });
        setLoading(true);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/download`, { spotify_link: spotifyLink });
            const { job_id } = response.data;
            setJobProgress(0);
            setStatusText('Starting download...');
            const es = new EventSource(`${API_BASE_URL}/api/download/events/${job_id}`);
            eventSourceRef.current = es;

            es.onmessage = (e) => {
                const data = JSON.parse(e.data);
                setJobProgress(data.progress);
                setStatusText(data.status || '');
                if (data.finished) {
                    es.close();
                    setLoading(false);
                    setDownloadMessage({ type: data.status === 'error' ? 'error' : 'success', text: data.message || '' });
                    setTimeout(() => setDownloadMessage(null), 5000);
                    setJobProgress(null);
                    fetchAlbums();
                }
            };

            es.onerror = () => {
                es.close();
                setLoading(false);
                setDownloadMessage({ type: 'error', text: 'Connection lost.' });
            };
        } catch (error) {
            console.error('Download error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'An unknown error occurred during download.';
            setDownloadMessage({ type: 'error', text: errorMessage });
        }
    }, [API_BASE_URL, fetchAlbums]); // Add fetchAlbums here

    // Wrap handleDeleteAlbum with useCallback
    // Its dependency is API_BASE_URL.
    // setAlbums and setDownloadMessage are state setters, which are stable by default
    // and don't need to be in the dependency array.
    const handleDeleteAlbum = useCallback(async (albumId) => {
        if (window.confirm('Are you sure you want to delete this album?')) {
            setDownloadMessage(null);
            try {
                const response = await axios.delete(`${API_BASE_URL}/api/albums/${albumId}`);
                if (response.data.success) {
                    // Use functional update for state when new state depends on previous state
                    setAlbums(prevAlbums => prevAlbums.filter(album => album.id !== albumId));
                    setDownloadMessage({ type: 'success', text: response.data.message });
                } else {
                    const data = response.data;
                    setDownloadMessage({ type: 'error', text: data.message || 'Failed to delete album.' });
                }
            } catch (error) {
                console.error('Delete album error:', error);
                setDownloadMessage({ type: 'error', text: 'An error occurred while deleting the album.' });
            } finally {
                setTimeout(() => setDownloadMessage(null), 3000);
            }
        }
    }, [API_BASE_URL]); // Add API_BASE_URL here

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


    return (
        <div className="min-h-screen bg-gray-900 text-white"> {/* Added this wrapper div */}
            <div className="container mx-auto p-4"> {/* Removed redundant text-white and min-h-screen here */}
                <h1 className="text-4xl font-bold text-center mb-8">My Spotify Downloader</h1> {/* text-white already covered by parent */}
    
                <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
                    <h2 className="text-2xl font-semibold text-white mb-4">Download from Spotify</h2>
                    <DownloadForm onSubmit={handleDownload} loading={loading} />
                    {jobProgress !== null && (
                        <div className="mt-4">
                            <div className="w-full bg-gray-700 rounded">
                                <div className="bg-blue-500 h-4 rounded" style={{ width: `${jobProgress}%` }}></div>
                            </div>
                            <p className="text-sm mt-2 text-gray-300">{statusText} {Math.round(jobProgress)}%</p>
                        </div>
                    )}
                    {downloadMessage && <Message type={downloadMessage.type} text={downloadMessage.text} />}
                </div>
    
                <div className="bg-gray-800 p-6 rounded-lg shadow-lg">
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
                                pageType="history"
                            />
                        )
                    )}
                </div>
            </div>
        </div>
    );
}

export default SpotifyDownloadPage;