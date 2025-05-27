// frontend/src/pages/AlbumDetailsPage.js
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { formatDuration } from '../utils/helpers'; // Assuming you'll have a helper for duration formatting

function AlbumDetailsPage() {
    const { albumId } = useParams(); // Get albumId from URL parameters
    const [albumDetails, setAlbumDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchAlbumDetails = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await fetch(`/api/album_details/${albumId}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                setAlbumDetails(data);
            } catch (e) {
                console.error("Failed to fetch album details:", e);
                setError("Failed to load album details. Please try again.");
            } finally {
                setLoading(false);
            }
        };

        if (albumId) {
            fetchAlbumDetails();
        }
    }, [albumId]); // Re-fetch when albumId changes

    if (loading) {
        return <p className="text-center text-blue-600 text-xl mt-8">Loading album details...</p>;
    }

    if (error) {
        return <p className="text-center text-red-600 text-xl mt-8">{error}</p>;
    }

    if (!albumDetails) {
        return <p className="text-center text-gray-500 text-xl mt-8">Album not found.</p>;
    }

    return (
        <div className="container mx-auto p-6 text-white">
            <div className="flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-x-8">
                {/* Album Cover */}
                <img
                    src={albumDetails.image_url || 'https://via.placeholder.com/300x300.png?text=No+Cover'}
                    alt={`${albumDetails.title} Album Cover`}
                    className="w-full md:w-1/3 lg:w-1/4 rounded-lg shadow-xl"
                />

                {/* Album Info */}
                <div className="flex-1 text-center md:text-left">
                    <h1 className="text-4xl font-bold mb-2">{albumDetails.title}</h1>
                    <p className="text-xl text-gray-400 mb-2">by {albumDetails.artist}</p>
                    <p className="text-md text-gray-500 mb-1">
                        Release Date: {albumDetails.release_date ? new Date(albumDetails.release_date).toLocaleDateString() : 'N/A'}
                    </p>
                    <p className="text-md text-gray-500">Total Tracks: {albumDetails.total_tracks}</p>
                    {albumDetails.spotify_url && (
                        <a
                            href={albumDetails.spotify_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block mt-4 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-4 rounded-full transition duration-200"
                        >
                            Listen on Spotify
                        </a>
                    )}
                </div>
            </div>

            {/* Tracks List */}
            <div className="mt-12">
                <h2 className="text-3xl font-semibold mb-6 text-center md:text-left">Tracks</h2>
                {albumDetails.tracks && albumDetails.tracks.length > 0 ? (
                    <ul className="space-y-2">
                        {albumDetails.tracks.map((track, index) => (
                            <li
                                key={track.spotify_id || index}
                                className="bg-gray-800 p-4 rounded-lg shadow flex flex-col sm:flex-row justify-between items-center"
                            >
                                <div className="flex-1 text-left mb-2 sm:mb-0">
                                    <p className="text-lg font-medium">{track.track_number}. {track.title}</p>
                                    <p className="text-sm text-gray-400">
                                        {track.artists.join(', ')}
                                    </p>
                                </div>
                                <p className="text-gray-400 text-sm">
                                    {formatDuration(track.duration_ms)}
                                </p>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="text-gray-500 text-lg">No tracks found for this album.</p>
                )}
            </div>
        </div>
    );
}

export default AlbumDetailsPage;