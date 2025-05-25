// src/App.js
import React, { useState, useEffect } from 'react';
import axios from 'axios'; // Or use native fetch
import DownloadForm from './components/DownloadForm';
import AlbumGallery from './components/AlbumGallery';
import Message from './components/Message';
import './App.css'; // Your main CSS for global styles

function App() {
    const [message, setMessage] = useState(null); // { type: 'success', text: '...' }
    const [albums, setAlbums] = useState([]);
    const [loading, setLoading] = useState(false);

    const API_BASE_URL = process.env.NODE_ENV === 'production' 
                         ? window.location.origin 
                         : 'http://localhost:5000'; // Flask backend URL

    const fetchAlbums = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_BASE_URL}/api/albums`);
            setAlbums(response.data);
        } catch (error) {
            console.error('Error fetching albums:', error);
            setMessage({ type: 'error', text: 'Failed to load albums.' });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAlbums();
    }, []);

    const handleDownload = async (spotifyLink) => {
        setLoading(true);
        setMessage(null); // Clear previous messages
        try {
            const response = await axios.post(`${API_BASE_URL}/api/download`, { spotify_link: spotifyLink });
            setMessage({ type: 'success', text: response.data.message });
            // After successful download, refresh the album list
            fetchAlbums();
        } catch (error) {
            console.error('Download error:', error);
            const errorMessage = error.response?.data?.message || error.message || 'An unknown error occurred during download.';
            setMessage({ type: 'error', text: errorMessage });
        } finally {
            setLoading(false);
        }
    };

    const handleToggleFavorite = async (albumId) => {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/albums/${albumId}/favorite`);
            if (response.data.success) {
                setAlbums(albums.map(album =>
                    album.id === albumId ? { ...album, is_favorite: response.data.is_favorite } : album
                ));
            } else {
                setMessage({ type: 'error', text: 'Failed to toggle favorite status.' });
            }
        } catch (error) {
            console.error('Favorite toggle error:', error);
            setMessage({ type: 'error', text: 'An error occurred while updating favorite status.' });
        }
    };

    const handleDeleteAlbum = async (albumId) => {
        if (window.confirm('Are you sure you want to delete this album?')) {
            try {
                const response = await axios.delete(`${API_BASE_URL}/api/albums/${albumId}`);
                if (response.data.success) {
                    setAlbums(albums.filter(album => album.id !== albumId));
                    setMessage({ type: 'success', text: response.data.message });
                } else {
                    setMessage({ type: 'error', text: 'Failed to delete album.' });
                }
            } catch (error) {
                console.error('Delete album error:', error);
                setMessage({ type: 'error', text: 'An error occurred while deleting the album.' });
            }
        }
    };

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-4xl font-bold text-white text-center mb-8">CD Collector & Spotify Downloader</h1>

            <div className="bg-gray-700 p-6 rounded-lg shadow-lg mb-8">
                <h2 className="text-2xl font-semibold text-white mb-4">Download Spotify Content</h2>
                <DownloadForm onSubmit={handleDownload} loading={loading} />
                {message && <Message type={message.type} text={message.text} />}
            </div>

            <div className="bg-gray-700 p-6 rounded-lg shadow-lg">
                <h2 className="text-2xl font-semibold text-white mb-4">My CD Collection Gallery</h2>
                {loading && <p className="text-gray-300 text-center">Loading albums...</p>}
                {!loading && albums.length === 0 && <p className="text-gray-300 text-center">No albums in your collection yet. Add some!</p>}
                <AlbumGallery
                    albums={albums}
                    onToggleFavorite={handleToggleFavorite}
                    onDeleteAlbum={handleDeleteAlbum}
                />
            </div>
        </div>
    );
}

export default App;