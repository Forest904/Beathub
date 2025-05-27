// src/components/AlbumGallery.js
import React from 'react';
import AlbumCard from './AlbumCard.js';
import { useNavigate } from 'react-router-dom'; // Import useNavigate

function AlbumGallery({ albums, onToggleFavorite, onDeleteAlbum }) {
    const navigate = useNavigate(); // Initialize useNavigate

    const handleAlbumClick = (albumId) => {
        navigate(`/album/${albumId}`); // Navigate to the new album details page
    };

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {albums.map((album) => (
                <AlbumCard
                    key={album.id}
                    album={album}
                    onToggleFavorite={onToggleFavorite}
                    onDeleteAlbum={onDeleteAlbum}
                    onAlbumClick={handleAlbumClick} // Pass the new click handler
                />
            ))}
        </div>
    );
}

export default AlbumGallery;