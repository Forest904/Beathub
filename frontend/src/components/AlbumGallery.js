// src/components/AlbumGallery.js
import React from 'react';
import AlbumCard from './AlbumCard.js';
import { useNavigate } from 'react-router-dom'; // Import useNavigate

// Add 'pageType' to the destructured props
function AlbumGallery({ albums, onToggleFavorite, onDeleteAlbum, pageType }) {
    const navigate = useNavigate();

    const handleAlbumClick = (albumId) => {
        navigate(`/album/${albumId}`);
    };

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {albums.map((album) => (
                <AlbumCard
                    key={album.id}
                    album={album}
                    onToggleFavorite={onToggleFavorite}
                    onDeleteAlbum={onDeleteAlbum}
                    onAlbumClick={handleAlbumClick}
                    pageType={pageType}
                />
            ))}
        </div>
    );
}

export default AlbumGallery;