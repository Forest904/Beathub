// src/components/AlbumGallery.js
import React from 'react';
import AlbumCard from './AlbumCard.js';

function AlbumGallery({ albums, onToggleFavorite, onDeleteAlbum }) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {albums.map((album) => (
                <AlbumCard
                    key={album.id}
                    album={album}
                    onToggleFavorite={onToggleFavorite}
                    onDeleteAlbum={onDeleteAlbum}
                />
            ))}
        </div>
    );
}

export default AlbumGallery;