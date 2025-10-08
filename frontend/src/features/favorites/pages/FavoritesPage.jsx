import React, { useEffect, useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';

import FavoriteButton from '../components/FavoriteButton.jsx';
import {
  favoriteKeys,
  useFavoriteEvents,
  useFavoriteSummary,
  useFavoritesList,
} from '../hooks/useFavorites';
import FAVORITE_TOKENS, { FAVORITE_TYPES } from '../../../theme/tokens';
import { useAuth } from '../../../shared/hooks/useAuth';

const FILTERS = [{ key: 'all', label: 'All' }, ...FAVORITE_TYPES.map((type) => ({ key: type, label: type.charAt(0).toUpperCase() + type.slice(1) }))];

const FALLBACK_IMAGE = 'https://via.placeholder.com/200x200.png?text=No+Artwork';

const FavoriteCard = ({ favorite }) => {
  const metadata = useMemo(
    () => ({
      name: favorite.item_name,
      subtitle: favorite.item_subtitle,
      image_url: favorite.item_image_url,
      url: favorite.item_url,
    }),
    [favorite.item_name, favorite.item_subtitle, favorite.item_image_url, favorite.item_url],
  );

  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl bg-white shadow ring-1 ring-brand-100 transition hover:shadow-lg dark:bg-gray-800 dark:ring-gray-700">
      <div className="relative">
        <img
          src={favorite.item_image_url || FALLBACK_IMAGE}
          alt={favorite.item_name}
          className="h-48 w-full object-cover"
          loading="lazy"
        />
        <div className="absolute right-2 top-2">
          <FavoriteButton
            itemType={favorite.item_type}
            itemId={favorite.item_id}
            metadata={metadata}
            size="sm"
          />
        </div>
        <span
          className={`absolute left-2 top-2 ${FAVORITE_TOKENS.badgeClasses.base} ${FAVORITE_TOKENS.badgeClasses.active}`}
        >
          {favorite.item_type}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <h3 className="truncate text-lg font-semibold text-slate-900 dark:text-white">
          {favorite.item_name}
        </h3>
        {favorite.item_subtitle && (
          <p className="truncate text-sm text-slate-600 dark:text-gray-400">
            {favorite.item_subtitle}
          </p>
        )}
        <div className="mt-auto flex justify-between text-xs text-slate-500 dark:text-gray-400">
          <span>Added {new Date(favorite.created_at).toLocaleString()}</span>
          {favorite.item_url && (
            <a
              href={favorite.item_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 hover:text-brand-500 dark:text-brandDark-300"
            >
              Open
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

FavoriteCard.propTypes = {
  favorite: PropTypes.shape({
    item_type: PropTypes.string.isRequired,
    item_id: PropTypes.string.isRequired,
    item_name: PropTypes.string.isRequired,
    item_subtitle: PropTypes.string,
    item_image_url: PropTypes.string,
    item_url: PropTypes.string,
    created_at: PropTypes.string.isRequired,
  }).isRequired,
};

const FavoritesPage = () => {
  const { user, loading } = useAuth();
  const [activeFilter, setActiveFilter] = useState('all');
  const [page, setPage] = useState(1);
  const perPage = 12;
  const queryClient = useQueryClient();

  useFavoriteEvents(() => {
    queryClient.invalidateQueries({ queryKey: favoriteKeys.listPrefix });
    queryClient.invalidateQueries({ queryKey: favoriteKeys.summary });
  });

  useEffect(() => {
    setPage(1);
  }, [activeFilter]);

  const summaryQuery = useFavoriteSummary();
  const listQuery = useFavoritesList({
    page,
    perPage,
    type: activeFilter === 'all' ? undefined : activeFilter,
  });

  const favorites = listQuery.data?.items ?? [];
  const pagination = listQuery.data?.pagination ?? {};

  const summary = useMemo(() => summaryQuery.data?.summary || {}, [summaryQuery.data]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-50 dark:bg-slate-950">
        <p className="text-slate-600 dark:text-gray-300">Loading favourites…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-brand-50 dark:bg-slate-950">
        <div className="rounded-2xl bg-white p-8 text-center shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:text-gray-200 dark:ring-gray-700">
          <h1 className="mb-4 text-3xl font-semibold text-slate-900 dark:text-white">Sign in to view favourites</h1>
          <p className="mb-6 text-slate-600 dark:text-gray-400">
            Save artists, albums, and tracks once you are logged in.
          </p>
          <Link
            to="/login"
            className="rounded-full bg-brand-600 px-4 py-2 font-medium text-white transition hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400"
          >
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-50 py-8 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl px-4">
        <header className="mb-8 rounded-2xl bg-white p-6 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:ring-gray-700">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Your favourites</h1>
              <p className="text-slate-600 dark:text-gray-400">
                Quick access to artists, albums, and tracks you care about.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {FILTERS.map((filter) => {
                const count =
                  filter.key === 'all'
                    ? summary.total ?? 0
                    : summary[filter.key] ?? 0;
                const isActive = activeFilter === filter.key;
                return (
                  <button
                    key={filter.key}
                    type="button"
                    onClick={() => setActiveFilter(filter.key)}
                    className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                      isActive
                        ? 'border-brand-500 bg-brand-100 text-brand-700 dark:border-brandDark-400 dark:bg-brandDark-900/40 dark:text-brandDark-200'
                        : 'border-transparent bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                    }`}
                  >
                    {filter.label}
                    <span className={`${FAVORITE_TOKENS.badgeClasses.base} ${FAVORITE_TOKENS.badgeClasses.inactive}`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        <section className="rounded-2xl bg-white p-6 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:ring-gray-700">
          {listQuery.isLoading ? (
            <div className="flex min-h-[200px] items-center justify-center text-slate-600 dark:text-gray-300">
              Loading favourites…
            </div>
          ) : favorites.length === 0 ? (
            <div className="flex min-h-[200px] flex-col items-center justify-center gap-3 text-center">
              <span className="text-6xl">{FAVORITE_TOKENS.icon.inactive}</span>
              <p className="max-w-md text-slate-600 dark:text-gray-400">
                No favourites found yet. Browse artists or albums and tap the star icon to pin them here.
              </p>
            </div>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {favorites.map((favorite) => (
                  <FavoriteCard key={`${favorite.item_type}:${favorite.item_id}`} favorite={favorite} />
                ))}
              </div>
              <div className="mt-6 flex items-center justify-between text-sm text-slate-600 dark:text-gray-400">
                <span>
                  Page {pagination.page || 1} of {pagination.pages || 1}
                </span>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={!pagination.has_prev}
                    className={`rounded-full px-4 py-2 font-medium ${
                      pagination.has_prev
                        ? 'bg-brand-600 text-white hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400'
                        : 'bg-slate-200 text-slate-500 dark:bg-gray-700 dark:text-gray-500'
                    }`}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((prev) => (pagination.has_next ? prev + 1 : prev))}
                    disabled={!pagination.has_next}
                    className={`rounded-full px-4 py-2 font-medium ${
                      pagination.has_next
                        ? 'bg-brand-600 text-white hover:bg-brand-500 dark:bg-brandDark-500 dark:hover:bg-brandDark-400'
                        : 'bg-slate-200 text-slate-500 dark:bg-gray-700 dark:text-gray-500'
                    }`}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
};

export default FavoritesPage;
