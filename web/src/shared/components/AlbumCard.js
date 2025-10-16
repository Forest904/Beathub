import React, { useCallback } from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import FavoriteButton from '../../features/favorites/components/FavoriteButton.jsx';
import FAVORITE_TOKENS from '../../theme/tokens';

export const AlbumCardVariant = Object.freeze({
  DISCOVERY: 'discography',
  HISTORY: 'history',
  BURN_SELECTION: 'burn-selection',
});

const FALLBACK_IMAGE = 'https://via.placeholder.com/200x200.png?text=No+Cover';

const AlbumCard = ({ album, onDelete, onSelect, variant, isSelected, disabled }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isBestOf = String(album?.id || '').startsWith('bestof:');
  const displayName = album?.name || album?.title || 'Untitled Item';
  const subHeading = !isBestOf
    ? album?.artist || (album?.title && album.title !== displayName ? album.title : '')
    : '';
  const favoriteMetadata = {
    name: displayName,
    subtitle: subHeading,
    image_url: album?.image_url,
    cover_url: album?.image_url,
    spotify_url: album?.spotify_url,
  };
  const badgeLabel = isBestOf ? 'Best Of' : 'Album';
  const badgeClassName = `${FAVORITE_TOKENS.badgeClasses.base} ${isBestOf ? 'bg-brandSuccess-100 text-brandSuccess-700 dark:bg-brandSuccess-700/30 dark:text-brandSuccess-300' : FAVORITE_TOKENS.badgeClasses.active}`;

  const handleCopyLink = useCallback(
    (event) => {
      event.stopPropagation();
      if (!album.spotify_url) {
        return;
      }

      navigator.clipboard
        .writeText(album.spotify_url)
        .then(() => window.alert('Spotify link copied to clipboard!'))
        .catch((error) => {
          console.error('Failed to copy text: ', error);
          window.alert(`Failed to copy link. Please copy manually: ${album.spotify_url}`);
        });
    },
    [album.spotify_url],
  );

  const handleDirectDownload = useCallback(
    (event) => {
      event.stopPropagation();
      if (!album.spotify_url) {
        window.alert('Spotify URL not available for direct download.');
        return;
      }

      navigate('/download', { state: { spotifyLinkToDownload: album.spotify_url } });
    },
    [album.spotify_url, navigate],
  );

  const handleDelete = useCallback(
    (event) => {
      event.stopPropagation();
      if (typeof onDelete === 'function') {
        onDelete(album.id);
      }
    },
    [album.id, onDelete],
  );

  const handleCardClick = useCallback(() => {
    if (disabled) return;
    if (variant === AlbumCardVariant.DISCOVERY) {
      if (typeof onSelect === 'function') {
        onSelect(album);
      } else {
        navigate(`/album/${album.id}`);
      }
      return;
    }

    if (variant === AlbumCardVariant.HISTORY) {
      if (typeof onSelect === 'function') {
        onSelect(album);
      } else if (album.spotify_url) {
        window.open(album.spotify_url, '_blank', 'noopener,noreferrer');
      }
      return;
    }

    if (variant === AlbumCardVariant.BURN_SELECTION) {
      if (typeof onSelect === 'function') {
        onSelect(album);
      }
    }
  }, [album, disabled, navigate, onSelect, variant]);

  return (
    <div
      onClick={handleCardClick}
      className={`album-card bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transform transition duration-200 ring-1 ring-brand-100 dark:ring-0 ${
        disabled ? 'cursor-not-allowed opacity-70' : 'hover:scale-105 cursor-pointer'
      } ${
        isSelected ? 'border-4 border-brand-500' : 'border-2 border-transparent'
      }`}
    >
      <div className="relative w-full aspect-square overflow-hidden">
        <img
          src={album.image_url || FALLBACK_IMAGE}
          alt={`${displayName} Album Cover`}
          className="w-full h-full object-cover"
          width="640"
          height="640"
          loading="lazy"
        />
        <div className="absolute left-3 right-3 top-3 flex items-start justify-between gap-2">
          <span className={badgeClassName}>
            {badgeLabel}
          </span>
          {!isBestOf && (
            <div className="flex-shrink-0">
              <FavoriteButton
                itemType="album"
                itemId={String(album.id)}
                metadata={favoriteMetadata}
                size="sm"
              />
            </div>
          )}
        </div>
      </div>
      <div className="p-4 text-center">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1 truncate">{displayName}</h3>
        {!isBestOf && subHeading && (
          <p className="text-sm text-slate-600 dark:text-gray-400 mb-3 truncate">{subHeading}</p>
        )}
        <div className="flex flex-col space-y-2">
          {variant !== AlbumCardVariant.BURN_SELECTION && album.spotify_url && !isBestOf && (
            <button
              type="button"
              onClick={handleCopyLink}
              className="bg-brand-600 hover:bg-brand-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
            >
              Copy Spotify Link
            </button>
          )}

          {variant === AlbumCardVariant.DISCOVERY && album.spotify_url && !isBestOf && user && (
            <button
              type="button"
              onClick={handleDirectDownload}
              className="bg-brand-700 hover:bg-brand-800 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
            >
              Direct Download
            </button>
          )}

          {variant === AlbumCardVariant.HISTORY && typeof onDelete === 'function' && (
            <button
              type="button"
              onClick={handleDelete}
              className="bg-brandError-600 hover:bg-brandError-700 text-white font-medium py-2 px-3 rounded-md transition duration-150 text-sm"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

AlbumCard.propTypes = {
  album: PropTypes.shape({
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    artist: PropTypes.string,
    title: PropTypes.string,
    image_url: PropTypes.string,
    spotify_url: PropTypes.string,
  }).isRequired,
  onDelete: PropTypes.func,
  onSelect: PropTypes.func,
  variant: PropTypes.oneOf(Object.values(AlbumCardVariant)),
  isSelected: PropTypes.bool,
  disabled: PropTypes.bool,
};

AlbumCard.defaultProps = {
  onDelete: undefined,
  onSelect: undefined,
  variant: AlbumCardVariant.DISCOVERY,
  isSelected: false,
  disabled: false,
};

export default AlbumCard;

