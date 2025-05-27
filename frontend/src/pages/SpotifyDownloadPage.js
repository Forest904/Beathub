// src/pages/SpotifyDownloadPage.js
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom'; // Import useNavigate for handleAlbumCardClick
import DownloadForm from '../components/DownloadForm';
import AlbumGallery from '../components/AlbumGallery';
import Message from '../components/Message';

function SpotifyDownloadPage() {
    const location = useLocation();
    const navigate = useNavigate(); // Initialize useNavigate
    const [downloadMessage, setDownloadMessage] = useState(null);
    const [albums, setAlbums] = useState([]);
    const [loading, setLoading] = useState(false);
    const [initialFetchComplete, setInitialFetchComplete] = useState(false);
    const autoDownloadAttempted = useRef(false);

    const API_BASE_URL = process.env.NODE_ENV === 'production'
        ? window.location.origin
        : 'http://localhost:5000';

    const fetchAlbums = async () => {
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
    };

    const handleDownload = async (spotifyLink) => {
        setDownloadMessage({ type: 'info', text: "Initiating download..." });
        setLoading(true);

        try {
            const response = await axios.post(`${API_BASE_URL}/api/download`, { spotify_link: spotifyLink });
            setDownloadMessage({ type: 'success', text: response.data.message });
            await fetchAlbums();
        } catch (error) {
            console.error('Download error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'An unknown error occurred during download.';
            setDownloadMessage({ type: 'error', text: errorMessage });
        } finally {
            setLoading(false);
            setTimeout(() => setDownloadMessage(null), 5000);
        }
    };

    useEffect(() => {
        fetchAlbums();

        if (location.state && location.state.spotifyLinkToDownload && !autoDownloadAttempted.current) {
            const linkToDownload = location.state.spotifyLinkToDownload;
            handleDownload(linkToDownload);
            autoDownloadAttempted.current = true;
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [location.state]);

    const handleToggleFavorite = async (albumId) => {
        setDownloadMessage(null);
        try {
            const response = await axios.post(`${API_BASE_URL}/api/albums/${albumId}/favorite`);
            if (response.data.success) {
                setAlbums(albums.map(album =>
                    album.id === albumId ? { ...album, is_favorite: response.data.is_favorite } : album
                ));
            } else {
                setDownloadMessage({ type: 'error', text: 'Failed to toggle favorite status.' });
            }
        } catch (error) {
            console.error('Favorite toggle error:', error);
            setDownloadMessage({ type: 'error', text: 'An error occurred while updating favorite status.' });
        }
    };

    const handleDeleteAlbum = async (albumId) => {
        if (window.confirm('Are you sure you want to delete this album?')) {
            setDownloadMessage(null);
            try {
                const response = await axios.delete(`${API_BASE_URL}/api/albums/${albumId}`);
                if (response.data.success) {
                    setAlbums(albums.filter(album => album.id !== albumId));
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
    };

    // Handler for when an album card in the collection is clicked
    const handleAlbumCardClick = (albumId) => {
        navigate(`/album/${albumId}`);
    };

    return (
        <div className="container mx-auto p-4 min-h-screen">
            <h1 className="text-4xl font-bold text-white text-center mb-8">My Spotify Downloader</h1>

            <div className="bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
                <h2 className="text-2xl font-semibold text-white mb-4">Download from Spotify</h2>
                <DownloadForm onSubmit={handleDownload} loading={loading} />
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
                            onToggleFavorite={handleToggleFavorite}
                            onDeleteAlbum={handleDeleteAlbum}
                            onAlbumClick={handleAlbumCardClick} // Pass the click handler for navigating to album details
                            pageType="history" 
                        />
                    )
                )}
            </div>
        </div>
    );
}

export default SpotifyDownloadPage;