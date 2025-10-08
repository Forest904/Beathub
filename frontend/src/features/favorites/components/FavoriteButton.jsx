import React from 'react';
import PropTypes from 'prop-types';

import FAVORITE_TOKENS from '../../../theme/tokens';
import { useAuth } from '../../../shared/hooks/useAuth';
import {
  useFavoriteStatus,
  useToggleFavorite,
} from '../hooks/useFavorites';

const FavoriteButton = ({ itemType, itemId, metadata, className, size }) => {
  const { user } = useAuth();
  const status = useFavoriteStatus(itemType, itemId);
  const toggleFavorite = useToggleFavorite();

  if (!user || !itemType || !itemId) {
    return null;
  }

  const favorited = Boolean(status.data?.favorited);
  const icon = favorited
    ? FAVORITE_TOKENS.icon.active
    : FAVORITE_TOKENS.icon.inactive;

  const iconClassName = [
    FAVORITE_TOKENS.iconClasses.base,
    favorited
      ? FAVORITE_TOKENS.iconClasses.active
      : FAVORITE_TOKENS.iconClasses.inactive,
    size === 'sm' ? 'text-xl' : '',
    size === 'lg' ? 'text-3xl' : '',
    className || '',
  ]
    .filter(Boolean)
    .join(' ');

  const handleToggle = (event) => {
    event.stopPropagation();
    toggleFavorite.mutate({
      item_type: itemType,
      item_id: itemId,
      metadata,
    });
  };

  return (
    <button
      type="button"
      aria-pressed={favorited}
      onClick={handleToggle}
      className="inline-flex items-center justify-center"
      title={favorited ? 'Remove from favourites' : 'Add to favourites'}
    >
      <span className={iconClassName}>{icon}</span>
    </button>
  );
};

FavoriteButton.propTypes = {
  itemType: PropTypes.oneOf(['artist', 'album', 'track']).isRequired,
  itemId: PropTypes.string.isRequired,
  metadata: PropTypes.shape({
    name: PropTypes.string,
    title: PropTypes.string,
    subtitle: PropTypes.string,
    artist: PropTypes.string,
    image_url: PropTypes.string,
    cover_url: PropTypes.string,
    url: PropTypes.string,
    spotify_url: PropTypes.string,
  }),
  className: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
};

FavoriteButton.defaultProps = {
  metadata: {},
  className: '',
  size: 'md',
};

export default FavoriteButton;
