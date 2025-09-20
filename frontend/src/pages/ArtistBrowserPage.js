import React, { useEffect, useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import SearchBar from '../components/SearchBar';
import ArtistGallery from '../components/ArtistGallery';
import useDebounce from '../hooks/useDebounce';
import Arrows from '../components/Arrows';
import { useSearchParams } from 'react-router-dom';

const ArtistBrowserPage = () => {
  const POPULAR_LIMIT = 20; // also used as page size for search
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialPage = Math.max(1, parseInt(searchParams.get('page') || '1', 10));

  const [searchTerm, setSearchTerm] = useState(initialQuery);
  const [artists, setArtists] = useState([]);
  const [famousArtists, setFamousArtists] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pageInfo, setPageInfo] = useState({ page: initialPage, hasNext: false, hasPrev: false, totalPages: 1, total: 0 });

  const debouncedSearchTerm = useDebounce(searchTerm, 500);
  const page = useMemo(() => Math.max(1, parseInt(searchParams.get('page') || '1', 10)), [searchParams]);

  const loadFamousArtists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/famous_artists', {
        params: { limit: POPULAR_LIMIT, page },
      });
      const data = response.data || {};
      setFamousArtists(data.artists || []);
      const p = data.pagination || {};
      setPageInfo({
        page: p.page || page,
        hasNext: Boolean(p.has_next),
        hasPrev: Boolean(p.has_prev) || page > 1,
        totalPages: p.total_pages || 1,
        total: p.total || (data.artists ? data.artists.length : 0),
      });
    } catch (fetchError) {
      console.error('Error fetching famous artists', fetchError);
      setError('Failed to load famous artists. Please try again later.');
      setPageInfo({ page: 1, hasNext: false, hasPrev: false, totalPages: 1, total: 0 });
    } finally {
      setLoading(false);
    }
  }, [POPULAR_LIMIT, page]);

  // Load famous artists when there is no active search term, and when page changes
  useEffect(() => {
    if (!debouncedSearchTerm || debouncedSearchTerm.length < 2) {
      loadFamousArtists();
    }
  }, [loadFamousArtists, debouncedSearchTerm, page]);

  useEffect(() => {
    const searchArtists = async () => {
      if (!debouncedSearchTerm || debouncedSearchTerm.length < 2) {
        setArtists([]);
        setPageInfo({ page: 1, hasNext: false, hasPrev: false, totalPages: 1, total: 0 });
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get('/api/search_artists', {
          params: { q: debouncedSearchTerm, page, limit: POPULAR_LIMIT },
        });
        const data = response.data || {};
        setArtists(data.artists || []);
        const p = data.pagination || {};
        setPageInfo({
          page: p.page || page,
          hasNext: Boolean(p.has_next),
          hasPrev: Boolean(p.has_prev),
          totalPages: p.total_pages || 1,
          total: p.total || (data.artists ? data.artists.length : 0),
        });
      } catch (searchError) {
        console.error('Error searching artists', searchError);
        setError(`Failed to search for "${debouncedSearchTerm}". Please try again.`);
        setArtists([]);
        setPageInfo({ page: 1, hasNext: false, hasPrev: false, totalPages: 1, total: 0 });
      } finally {
        setLoading(false);
      }
    };

    searchArtists();
  }, [debouncedSearchTerm, page]);

  const handleSearchChange = (event) => {
    const value = event.target.value;
    setSearchTerm(value);
    // Keep URL in sync and reset page -> 1 on search change
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set('q', value);
      next.set('page', '1');
    } else {
      next.delete('q');
      next.set('page', '1');
    }
    setSearchParams(next);
  };

  const goPrev = () => {
    if (page <= 1) return;
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page - 1));
    setSearchParams(next);
  };

  const goNext = () => {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(page + 1));
    setSearchParams(next);
  };

  // Ensure page param defaults to 1 on first mount
  useEffect(() => {
    if (!searchParams.get('page')) {
      const next = new URLSearchParams(searchParams);
      next.set('page', '1');
      setSearchParams(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center text-slate-900 dark:text-white mb-10">Discover Artists</h1>

        <SearchBar searchTerm={searchTerm} onSearchChange={handleSearchChange} placeholder="Search for your favorite artists..." />

        {loading && <p className="text-center text-brand-600 dark:text-brandDark-400 text-xl mt-8">Loading artists...</p>}

        {error && <p className="text-center text-brandError-600 dark:text-brandError-400 text-xl mt-8">{error}</p>}

        {!loading && !error && (
          <>
            {searchTerm ? (
              <section className="mb-12">
                <h2 className="text-3xl font-semibold text-slate-900 dark:text-white mb-6 text-center">
                  Search Results
                </h2>
                {artists.length > 0 ? (
                  <>
                    <ArtistGallery artists={artists} />
                    <Arrows
                      page={pageInfo.page}
                      hasPrev={pageInfo.hasPrev || page > 1}
                      hasNext={pageInfo.hasNext}
                      onPrev={goPrev}
                      onNext={goNext}
                    />
                  </>
                ) : (
                  <p className="text-center text-slate-500 dark:text-gray-400 text-lg">No artists found for "{searchTerm}".</p>
                )}
              </section>
            ) : (
              <section>
                <h2 className="text-3xl font-semibold text-slate-900 dark:text-white mb-6 text-center">Famous Artists</h2>
                {famousArtists.length > 0 ? (
                  <>
                    <ArtistGallery artists={famousArtists} />
                    <Arrows
                      page={pageInfo.page}
                      hasPrev={pageInfo.hasPrev || page > 1}
                      hasNext={pageInfo.hasNext}
                      onPrev={goPrev}
                      onNext={goNext}
                    />
                  </>
                ) : (
                  <p className="text-center text-slate-500 dark:text-gray-400 text-lg">No famous artists to display.</p>
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
