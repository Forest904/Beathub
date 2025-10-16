import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import FavoriteButton from '../../favorites/components/FavoriteButton.jsx';
import FAVORITE_TOKENS from '../../../theme/tokens';

const FALLBACK_IMAGE = 'https://via.placeholder.com/150?text=No+Image';

const ArtistCard = ({ artist }) => {
  const imageUrl = artist.image || FALLBACK_IMAGE;
  const hasFollowers = typeof artist.followers === 'number';
  const hasPopularity = typeof artist.popularity === 'number';
  const metricsUnavailable =
    (!artist.popularity_available && !hasPopularity) ||
    (!artist.followers_available && !hasFollowers);
  const genresLabel =
    Array.isArray(artist.genres) && artist.genres.length > 0
      ? artist.genres.slice(0, 3).join(', ')
      : null;
  const spotifyUrl = artist.external_urls?.spotify || artist.spotify_url || null;
  const favoriteMetadata = {
    name: artist.name,
    subtitle: genresLabel || undefined,
    image_url: imageUrl,
    url: spotifyUrl || undefined,
    spotify_url: spotifyUrl || undefined,
  };

  return (
    <Link to={`/artist/${artist.id}`} className="block transform transition-transform duration-200 hover:scale-105">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden flex flex-col h-full ring-1 ring-brand-100 dark:ring-0">
        <div className="relative w-full h-48 sm:h-56 md:h-64 overflow-hidden">
          <img src={imageUrl} alt={artist.name} className="w-full h-full object-cover" />
          <div className="absolute left-3 right-3 top-3 flex items-start justify-between gap-2">
            <span className={`${FAVORITE_TOKENS.badgeClasses.base} ${FAVORITE_TOKENS.badgeClasses.active}`}>
              Artist
            </span>
            <div className="flex-shrink-0">
              <FavoriteButton itemType="artist" itemId={String(artist.id)} metadata={favoriteMetadata} size="sm" />
            </div>
          </div>
        </div>
        <div className="p-4 flex flex-col flex-grow gap-2">
          <h3 className="text-xl font-semibold text-slate-900 dark:text-white truncate">{artist.name}</h3>
          {metricsUnavailable && (
            <span className="self-start inline-block text-xs px-2 py-1 rounded bg-slate-100 text-slate-600 dark:bg-gray-700 dark:text-gray-300">
              Metrics unavailable
            </span>
          )}
          {(hasFollowers || hasPopularity) && (
            <div className="flex items-center gap-2">
              {hasFollowers && (
                <span className="inline-flex items-center gap-2 rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 dark:border-brandDark-400 dark:bg-brandDark-500/20 dark:text-brandDark-100">
                  <span className="uppercase tracking-wide">Followers</span>
                  <span className="text-sm font-bold">
                    {artist.followers.toLocaleString()}
                  </span>
                </span>
              )}
              {hasPopularity && (
                <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100">
                  <span className="uppercase tracking-wide">Popularity</span>
                  <span className="text-sm font-bold">
                    {artist.popularity}
                  </span>
                </span>
              )}
            </div>
          )}
          {artist.genres?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {artist.genres.slice(0, 4).map((genre) => (
                <span
                  key={genre}
                  className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
                >
                  {genre.charAt(0).toUpperCase() + genre.slice(1)}
                </span>
              ))}
              {artist.genres.length > 4 && (
                <span className="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100">
                  +{artist.genres.length - 4}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
};

ArtistCard.propTypes = {
  artist: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    image: PropTypes.string,
    genres: PropTypes.arrayOf(PropTypes.string),
    followers: PropTypes.number,
    popularity: PropTypes.number,
    followers_available: PropTypes.bool,
    popularity_available: PropTypes.bool,
    spotify_url: PropTypes.string,
    external_urls: PropTypes.shape({
      spotify: PropTypes.string,
    }),
  }).isRequired,
};

export default ArtistCard;
