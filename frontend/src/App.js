// frontend/src/App.js (Revised)
import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import ArtistBrowserPage from './pages/ArtistBrowserPage';
import SpotifyDownloadPage from './pages/SpotifyDownloadPage';
import ArtistDetailsPage from './pages/ArtistDetailsPage';
import AlbumDetailsPage from './pages/AlbumDetailsPage';

import './App.css';

function App() {
    const [albums, setAlbums] = useState([]);
    const [message, setMessage] = useState('');
    const [messageType, setMessageType] = useState('');

    // Fetch albums only for the SpotifyDownloadPage
    const fetchAlbums = useCallback(async () => {
        try {
            const response = await fetch('/api/albums');
            if (!response.ok) {
                throw new Error('Failed to fetch albums');
            }
            const data = await response.json();
            setAlbums(data);
        } catch (error) {
            console.error("Error fetching albums:", error);
            setMessage("Failed to load albums.");
            setMessageType('error');
        }
    }, []);

    const handleToggleFavorite = async (albumId) => {
        try {
            const response = await fetch(`/api/albums/${albumId}/favorite`, {
                method: 'POST',
            });
            if (!response.ok) {
                throw new Error('Failed to toggle favorite status');
            }
            const updatedAlbum = await response.json();
            setAlbums(prevAlbums =>
                prevAlbums.map(album =>
                    album.id === albumId ? { ...album, is_favorite: updatedAlbum.is_favorite } : album
                )
            );
            setMessage(`Album "${updatedAlbum.title}" ${updatedAlbum.is_favorite ? 'added to' : 'removed from'} favorites.`);
            setMessageType('success');
        } catch (error) {
            console.error("Error toggling favorite:", error);
            setMessage("Failed to toggle favorite status.");
            setMessageType('error');
        }
    };

    const handleDeleteAlbum = async (albumId) => {
        if (window.confirm("Are you sure you want to delete this album?")) {
            try {
                const response = await fetch(`/api/albums/${albumId}`, {
                    method: 'DELETE',
                });
                if (!response.ok) {
                    throw new Error('Failed to delete album');
                }
                const result = await response.json();
                setAlbums(prevAlbums => prevAlbums.filter(album => album.id !== albumId));
                setMessage(result.message || 'Album deleted successfully.');
                setMessageType('success');
            } catch (error) {
                console.error("Error deleting album:", error);
                setMessage("Failed to delete album.");
                setMessageType('error');
            }
        }
    };

    return (
        <Router>
            <div className="min-h-screen bg-gray-900 text-white"> {/* Ensure this sets the base text color */}
                <Header />
                <main className="container mx-auto p-4">
                    {message && (
                        <div className={`p-3 mb-4 rounded text-center ${messageType === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white`}>
                            {message}
                        </div>
                    )}
                    <Routes>
                        <Route path="/" element={<ArtistBrowserPage />} /> {/* Landing page is now ArtistBrowserPage */}
                        <Route path="/download" element={<SpotifyDownloadPage albums={albums} onToggleFavorite={handleToggleFavorite} onDeleteAlbum={handleDeleteAlbum} fetchAlbums={fetchAlbums} />} /> {/* New route for download page */}
                        <Route path="/artist/:artistId" element={<ArtistDetailsPage />} />
                        <Route path="/album/:albumId" element={<AlbumDetailsPage />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}

export default App;