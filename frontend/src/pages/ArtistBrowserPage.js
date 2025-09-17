import React, { useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import SearchBar from '../components/SearchBar';
import ArtistGallery from '../components/ArtistGallery';
import useDebounce from '../hooks/useDebounce';

const ArtistBrowserPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [artists, setArtists] = useState([]);
  const [famousArtists, setFamousArtists] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const debouncedSearchTerm = useDebounce(searchTerm, 500);

  const loadFamousArtists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/famous_artists');
      setFamousArtists(response.data.artists);
    } catch (fetchError) {
      console.error('Error fetching famous artists', fetchError);
      setError('Failed to load famous artists. Please try again later.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFamousArtists();
  }, [loadFamousArtists]);

  useEffect(() => {
    const searchArtists = async () => {
      if (!debouncedSearchTerm || debouncedSearchTerm.length < 2) {
        setArtists([]);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get('/api/search_artists', {
          params: { q: debouncedSearchTerm },
        });
        setArtists(response.data.artists);
      } catch (searchError) {
        console.error('Error searching artists', searchError);
        setError(`Failed to search for "${debouncedSearchTerm}". Please try again.`);
        setArtists([]);
      } finally {
        setLoading(false);
      }
    };

    searchArtists();
  }, [debouncedSearchTerm]);

  const handleSearchChange = (event) => {
    setSearchTerm(event.target.value);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center text-white mb-10">Discover Artists</h1>

        <SearchBar searchTerm={searchTerm} onSearchChange={handleSearchChange} placeholder="Search for your favorite artists..." />

        {loading && <p className="text-center text-blue-400 text-xl mt-8">Loading artists...</p>}

        {error && <p className="text-center text-red-400 text-xl mt-8">{error}</p>}

        {!loading && !error && (
          <>
            {searchTerm ? (
              <section className="mb-12">
                <h2 className="text-3xl font-semibold text-white mb-6 text-center">
                  Search Results {artists.length > 0 && `(${artists.length})`}
                </h2>
                {artists.length > 0 ? (
                  <ArtistGallery artists={artists} />
                ) : (
                  <p className="text-center text-gray-400 text-lg">No artists found for "{searchTerm}".</p>
                )}
              </section>
            ) : (
              <section>
                <h2 className="text-3xl font-semibold text-white mb-6 text-center">Famous Artists</h2>
                {famousArtists.length > 0 ? (
                  <ArtistGallery artists={famousArtists} />
                ) : (
                  <p className="text-center text-gray-400 text-lg">No famous artists to display.</p>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ArtistBrowserPage;
