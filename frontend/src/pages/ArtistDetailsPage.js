import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import AlbumGallery from '../components/AlbumGallery';
import { AlbumCardVariant } from '../components/AlbumCard';

const FALLBACK_IMAGE = 'https://via.placeholder.com/200?text=No+Image';

const ArtistDetailsPage = () => {
  const { artistId } = useParams();
  const navigate = useNavigate();
  const [artistDetails, setArtistDetails] = useState(null);
  const [discography, setDiscography] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!artistId) {
      setError('Artist ID is missing.');
      setLoading(false);
      return;
    }

    let cancelled = false;

    const loadArtist = async () => {
      try {
        const [detailsResponse, discographyResponse] = await Promise.all([
          axios.get(`/api/artist_details/${artistId}`),
          axios.get(`/api/artist_discography/${artistId}`),
        ]);

        if (cancelled) {
          return;
        }

        setArtistDetails(detailsResponse.data);
        setDiscography(discographyResponse.data.discography);
        setError(null);
      } catch (requestError) {
        console.error('Failed to load artist profile', requestError);
        if (!cancelled) {
          setError('We could not load this artist right now. Please try again later.');
          setArtistDetails(null);
          setDiscography([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadArtist();

    return () => {
      cancelled = true;
    };
  }, [artistId]);

  const handleAlbumSelect = (album) => {
    navigate(`/album/${album.id}`);
  };

  const genresLabel = useMemo(() => {
    if (!artistDetails?.genres?.length) {
      return null;
    }
    return artistDetails.genres.join(', ');
  }, [artistDetails]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-xl mr-4">Loading artist information...</p>
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-center text-red-500 text-xl">{error}</p>
      </div>
    );
  }

  if (!artistDetails) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <p className="text-center text-gray-400 text-xl">No artist found with this ID.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <section className="bg-gray-800 rounded-lg shadow-lg p-6 mb-8 flex flex-col md:flex-row items-center md:items-center md:justify-center gap-6 max-w-5xl mx-auto">
          <div className="flex-shrink-0 md:mr-10">
            <img
              src={artistDetails.image || FALLBACK_IMAGE}
              alt={artistDetails.name}
              className="w-48 h-48 md:w-64 md:h-64 rounded-full object-cover shadow-md"
            />
          </div>
          <div className="text-center md:text-left flex-grow">
            <h1 className="text-5xl font-extrabold text-white mb-2">{artistDetails.name}</h1>
            {genresLabel && (
              <p className="text-lg text-gray-300 mb-2">
                <span className="font-semibold">Genres:</span> {genresLabel}
              </p>
            )}
            {typeof artistDetails.followers === 'number' && (
              <p className="text-lg text-gray-300 mb-2">
                <span className="font-semibold">Followers:</span> {artistDetails.followers.toLocaleString()}
              </p>
            )}
            {typeof artistDetails.popularity === 'number' && (
              <p className="text-lg text-gray-300 mb-4">
                <span className="font-semibold">Popularity:</span> {artistDetails.popularity}% on Spotify
              </p>
            )}
            {artistDetails.external_urls?.spotify && (
              <a
                href={artistDetails.external_urls.spotify}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center bg-green-500 hover:bg-green-600 text-white font-semibold py-2 px-5 rounded-full transition-colors duration-200"
              >
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 0C5.373 0 0 5.373 0 12c0 6.627 5.373 12 12 12s12-5.373 12-12C24 5.373 18.627 0 12 0zm5.433 17.415a1 1 0 0 1-1.383.333c-3.096-1.892-6.992-2.322-11.573-1.28a1 1 0 0 1-.433-1.949c5.063-1.126 9.433-.62 13.004 1.497a1 1 0 0 1 .385 1.399zm1.649-3.256a1 1 0 0 1-1.383.345c-3.546-2.169-8.956-2.806-13.161-1.544a1 1 0 1 1-.57-1.92c4.73-1.403 10.657-.695 14.801 1.847a1 1 0 0 1 .313 1.272zm.14-3.392c-4.262-2.523-11.303-2.754-15.365-1.53a1 1 0 1 1-.59-1.914c4.596-1.418 12.283-1.149 17.062 1.685a1 1 0 0 1-1.107 1.759z" />
                </svg>
                View on Spotify
              </a>
            )}
          </div>
        </section>

        <section className="bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-3xl font-bold text-white mb-6 text-center">Discography</h2>
          {discography.length > 0 ? (
            <AlbumGallery albums={discography} onSelect={handleAlbumSelect} variant={AlbumCardVariant.DISCOVERY} />
          ) : (
            <p className="text-center text-gray-400 text-lg">No albums or singles found for this artist.</p>
          )}
        </section>
      </div>
    </div>
  );
};

export default ArtistDetailsPage;
