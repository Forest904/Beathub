// src/components/AlbumCard.js
import React from 'react';

// Destructure onAlbumClick from props
function AlbumCard({ album, onToggleFavorite, onDeleteAlbum, onAlbumClick }) {
    const handleCopyLink = () => {
        navigator.clipboard.writeText(album.spotify_url)
            .then(() => alert('Spotify link copied to clipboard!'))
            .catch(err => {
                console.error('Failed to copy text: ', err);
                alert('Failed to copy link. Please copy manually: ' + album.spotify_url);
            });
    };

    // This function will handle the click on the album card itself,
    // preventing the default behavior and stopping event propagation
    // if a button inside the card is clicked.
    const handleClick = (e) => {
        // Prevent click from propagating to the card if a button was clicked
        if (e.target.tagName === 'BUTTON') {
            return;
        }
        // Call the onAlbumClick prop, passing the album's actual Spotify ID (album.id)
        if (onAlbumClick) {
            onAlbumClick(album.id); // CORRECTED: pass album.id
        }
    };

    return (
        // Make the entire card div clickable
        <div
            className="album-card bg-gray-800 rounded-lg shadow-md overflow-hidden transform transition duration-200 hover:scale-105 cursor-pointer"
            onClick={handleClick} // Attach the click handler to the card
        >
            <img
                src={album.image_url || 'https://via.placeholder.com/200x200.png?text=No+Cover'}
                alt={`${album.name} Album Cover`} // Changed to album.name for consistency
                className="w-full h-auto object-cover"
            />
            <div className="p-4 text-center">
                <h3 className="text-lg font-semibold text-white mb-1 truncate">{album.name}</h3>
                <p className="text-sm text-gray-400 mb-3 truncate">{album.artist}</p>
                <div className="flex flex-col space-y-2">
                    <button
                        onClick={handleCopyLink}
                        className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
                    >
                        Copy Spotify Link
                    </button>
                    <button
                        onClick={() => onToggleFavorite(album.id)}
                        className={`font-medium py-2 px-3 rounded-md transition duration-150 text-sm
                            ${album.is_favorite ? 'bg-yellow-500 hover:bg-yellow-600 text-gray-900' : 'bg-green-600 hover:bg-green-700 text-white'}`}
                    >
                        {album.is_favorite ? '❤️ Favorited' : '🤍 Add to Favorites'}
                    </button>
                    <button
                        onClick={() => onDeleteAlbum(album.id)}
                        className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
                    >
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
}

export default AlbumCard;