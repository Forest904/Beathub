// src/components/AlbumCard.js
import React from 'react';
import { useNavigate } from 'react-router-dom';

function AlbumCard({ album, onDeleteAlbum, onAlbumClick, pageType }) {
    const navigate = useNavigate();

    const handleCopyLink = () => {
        navigator.clipboard.writeText(album.spotify_url)
            .then(() => alert('Spotify link copied to clipboard!'))
            .catch(err => {
                console.error('Failed to copy text: ', err);
                alert('Failed to copy link. Please copy manually: ' + album.spotify_url);
            });
    };

    const handleDirectDownload = () => {
        if (album.spotify_url) {
            navigate('/download', { state: { spotifyLinkToDownload: album.spotify_url } });
        } else {
            alert('Spotify URL not available for direct download.');
        }
    };

    // Function to handle the click on the album card itself (excluding buttons)
    const handleClick = (e) => {
        // Prevent click from propagating to the card if a button was clicked
        if (e.target.tagName === 'BUTTON') {
            e.stopPropagation();
            return;
        }

        // Conditional navigation based on pageType
        if (pageType === 'discography') {
            if (onAlbumClick) {
                onAlbumClick(album.id);
            }
        } else if (pageType === 'history') {
            if (album.spotify_url) {
                window.open(album.spotify_url, '_blank', 'noopener,noreferrer');
            } else {
                alert('Spotify URL not available for this album.');
            }
        }
    };

    return (
        <div
            className="album-card bg-gray-800 rounded-lg shadow-md overflow-hidden transform transition duration-200 hover:scale-105 cursor-pointer"
            onClick={handleClick}
        >
            <img
                src={album.image_url || 'https://via.placeholder.com/200x200.png?text=No+Cover'}
                alt={`${album.name} Album Cover`}
                className="w-full h-auto object-cover"
            />
            <div className="p-4 text-center">
                <h3 className="text-lg font-semibold text-white mb-1 truncate">{album.name}</h3>
                <p className="text-sm text-gray-400 mb-3 truncate">{album.artist}</p>
                <div className="flex flex-col space-y-2">

                    {album.spotify_url && (
                        <button
                            onClick={handleCopyLink}
                            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
                        >
                            Copy Spotify Link
                        </button>
                    )}

                    {pageType === 'discography' && album.spotify_url && (
                        <button
                            onClick={handleDirectDownload}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
                        >
                            Direct Download
                        </button>
                    )}

                    {pageType === 'history' && onDeleteAlbum && (
                        <button
                            onClick={() => onDeleteAlbum(album.id)}
                            className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
                        >
                            Delete
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default AlbumCard;