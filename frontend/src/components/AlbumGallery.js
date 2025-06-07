// src/components/AlbumGallery.js
import React from 'react';
import AlbumCard from './AlbumCard.js';

function AlbumGallery({ albums, onDeleteAlbum, onAlbumClick, pageType }) {

    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {albums.map((album) => (
                <AlbumCard
                    key={album.id}
                    album={album}
                    onDeleteAlbum={onDeleteAlbum}
                    onAlbumClick={onAlbumClick}
                    pageType={pageType}
                />
            ))}
        </div>
    );
}

export default AlbumGallery;