// src/pages/ArtistDetailsPage.js
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import AlbumGallery from '../components/AlbumGallery'; // Assuming you have this
import Message from '../components/Message'; // For displaying error messages

function ArtistDetailsPage() {
    const { artistId } = useParams(); // Get artistId from the URL parameter
    const [artistDetails, setArtistDetails] = useState(null);
    const [discography, setDiscography] = useState([]);
    const [loadingArtist, setLoadingArtist] = useState(true);
    const [loadingDiscography, setLoadingDiscography] = useState(true);
    const [error, setError] = useState(null);

    const API_BASE_URL = process.env.NODE_ENV === 'production'
                            ? window.location.origin
                            : 'http://localhost:5000';

    // --- Effect to fetch Artist Details ---
    useEffect(() => {
        if (!artistId) {
            setError("Artist ID is missing.");
            setLoadingArtist(false);
            return;
        }

        const fetchArtistDetails = async () => {
            setLoadingArtist(true);
            setError(null);
            try {
                const response = await axios.get(`${API_BASE_URL}/api/artist_details/${artistId}`);
                setArtistDetails(response.data);
                console.log(`Workspaceed details for artist ${response.data.name}`); // Changed from logger.info
            } catch (err) {
                console.error("Error fetching artist details:", err);
                setError("Failed to load artist details.");
            } finally {
                setLoadingArtist(false);
            }
        };

        fetchArtistDetails();
    }, [artistId, API_BASE_URL]); // Re-run if artistId or base URL changes

    // --- Effect to fetch Artist Discography ---
    useEffect(() => {
        if (!artistId) {
            setLoadingDiscography(false);
            return;
        }

        const fetchDiscography = async () => {
            setLoadingDiscography(true);
            setError(null); // Clear error for discography specific to this fetch
            try {
                const response = await axios.get(`${API_BASE_URL}/api/artist_discography/${artistId}`);
                setDiscography(response.data.discography);
                console.log(`Workspaceed discography for artist ${artistId}. Found ${response.data.discography.length} items.`); // Changed from logger.info
            } catch (err) {
                console.error("Error fetching discography:", err);
                setError("Failed to load artist's discography.");
            } finally {
                setLoadingDiscography(false);
            }
        };

        fetchDiscography();
    }, [artistId, API_BASE_URL]); // Re-run if artistId or base URL changes

    if (loadingArtist || loadingDiscography) {
        return (
            <div className="text-center mt-12">
                <p className="text-gray-700 text-xl">Loading artist information and discography...</p>
                {/* Basic spinner, consider a dedicated Spinner component */}
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mt-4"></div>
            </div>
        );
    }

    if (error) {
        return <Message type="error" text={error} />;
    }

    if (!artistDetails) {
        return <Message type="info" text="No artist found with this ID." />;
    }

    return (
        <div className="container mx-auto px-4 py-8">
            {/* Artist Header Section */}
            <section className="bg-white rounded-lg shadow-lg p-6 mb-8 flex flex-col md:flex-row items-center md:items-start gap-6">
                <div className="flex-shrink-0">
                    <img
                        src={artistDetails.image || 'https://via.placeholder.com/200?text=No+Image'}
                        alt={artistDetails.name}
                        className="w-48 h-48 md:w-64 md:h-64 rounded-full object-cover shadow-md"
                    />
                </div>
                <div className="text-center md:text-left flex-grow">
                    <h1 className="text-5xl font-extrabold text-gray-900 mb-2">{artistDetails.name}</h1>
                    {artistDetails.genres && artistDetails.genres.length > 0 && (
                        <p className="text-lg text-gray-600 mb-2">
                            <span className="font-semibold">Genres:</span> {artistDetails.genres.join(', ')}
                        </p>
                    )}
                    {artistDetails.followers !== undefined && (
                        <p className="text-lg text-gray-600 mb-2">
                            <span className="font-semibold">Followers:</span> {artistDetails.followers.toLocaleString()}
                        </p>
                    )}
                    {artistDetails.popularity !== undefined && (
                        <p className="text-lg text-gray-600 mb-4">
                            <span className="font-semibold">Popularity:</span> {artistDetails.popularity}% (on Spotify)
                        </p>
                    )}
                    {artistDetails.external_urls && artistDetails.external_urls && (
                        <a
                            href={artistDetails.external_urls}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-5 rounded-full transition-colors duration-200"
                        >
                            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M12 0C5.372 0 0 5.372 0 12c0 6.627 5.372 12 12 12 6.627 0 12-5.373 12-12 0-6.628-5.373-12-12-12zm6.273 17.525c-.24-.316-.62-.48-1.04-.48-.42 0-.8.164-1.04.48-1.096 1.442-2.793 2.375-4.693 2.375-1.9 0-3.6-1.002-4.695-2.375-.24-.316-.62-.48-1.04-.48-.42 0-.8.164-1.04.48-1.096 1.442-2.793 2.375-4.693 2.375-1.9 0-3.6-1.002-4.695-2.375-.24-.316-.62-.48-1.04-.48-.42 0-.8.164-1.04.48-1.096 1.442-2.793 2.375-4.693 2.375-1.9 0-3.6-1.002-4.695-2.375"></path>
                            </svg>
                            View on Spotify
                        </a>
                    )}
                </div>
            </section>

            {/* Discography Section */}
            <section className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-3xl font-bold text-gray-800 mb-6 text-center">Discography</h2>
                {discography.length > 0 ? (
                    <AlbumGallery albums={discography} />
                ) : (
                    <p className="text-center text-gray-500 text-lg">No albums or singles found for this artist.</p>
                )}
            </section>
        </div>
    );
}

export default ArtistDetailsPage;