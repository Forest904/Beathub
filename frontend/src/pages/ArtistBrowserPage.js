// src/pages/ArtistBrowserPage.js
import React, { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import ArtistGallery from '../components/ArtistGallery';
import useDebounce from '../hooks/useDebounce';

function ArtistBrowserPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const [artists, setArtists] = useState([]);
  const [famousArtists, setFamousArtists] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Debounce the searchTerm to avoid too many API calls
  const debouncedSearchTerm = useDebounce(searchTerm, 500); // 500ms delay

  // Effect to fetch famous artists on initial load
  useEffect(() => {
    const fetchFamousArtists = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('http://localhost:5000/api/famous_artists');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setFamousArtists(data.artists);
      } catch (e) {
        setError("Failed to load famous artists. Please try again later.");
        console.error("Error fetching famous artists:", e);
      } finally {
        setLoading(false);
      }
    };

    fetchFamousArtists();
  }, []); // Empty dependency array means this runs once on mount

  // Effect to perform artist search when debouncedSearchTerm changes
  useEffect(() => {
    const searchSpotifyArtists = async () => {
      if (!debouncedSearchTerm || debouncedSearchTerm.length < 2) {
        setArtists([]); // Clear search results if query is too short or empty
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`http://localhost:5000/api/search_artists?q=${encodeURIComponent(debouncedSearchTerm)}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setArtists(data.artists);
      } catch (e) {
        setError(`Failed to search for "${debouncedSearchTerm}". Please try again.`);
        console.error("Error searching artists:", e);
        setArtists([]); // Clear results on error
      } finally {
        setLoading(false);
      }
    };

    searchSpotifyArtists();
  }, [debouncedSearchTerm]); // Re-run when the debounced search term changes

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold text-center text-gray-800 mb-10">Discover Artists</h1>

      <SearchBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        placeholder="Search for your favorite artists..."
      />

      {loading && (
        <p className="text-center text-blue-600 text-xl mt-8">Loading artists...</p>
      )}

      {error && (
        <p className="text-center text-red-600 text-xl mt-8">{error}</p>
      )}

      {!loading && !error && (
        <>
          {searchTerm ? (
            // Display search results if a search term is present
            <section className="mb-12">
              <h2 className="text-3xl font-semibold text-gray-700 mb-6 text-center">
                Search Results {artists.length > 0 && `(${artists.length})`}
              </h2>
              {artists.length > 0 ? (
                <ArtistGallery artists={artists} />
              ) : (
                <p className="text-center text-gray-500 text-lg">No artists found for "{searchTerm}".</p>
              )}
            </section>
          ) : (
            // Otherwise, display famous artists
            <section>
              <h2 className="text-3xl font-semibold text-gray-700 mb-6 text-center">Famous Artists</h2>
              {famousArtists.length > 0 ? (
                <ArtistGallery artists={famousArtists} />
              ) : (
                <p className="text-center text-gray-500 text-lg">No famous artists to display.</p>
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default ArtistBrowserPage;