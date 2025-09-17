import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

const FALLBACK_IMAGE = 'https://via.placeholder.com/150?text=No+Image';

const ArtistCard = ({ artist }) => {
  const imageUrl = artist.image || FALLBACK_IMAGE;

  return (
    <Link to={`/artist/${artist.id}`} className="block transform transition-transform duration-200 hover:scale-105">
      <div className="bg-gray-800 rounded-lg shadow-md overflow-hidden flex flex-col h-full">
        <div className="relative w-full h-48 sm:h-56 md:h-64 overflow-hidden">
          <img src={imageUrl} alt={artist.name} className="w-full h-full object-cover" />
        </div>
        <div className="p-4 flex flex-col justify-between flex-grow">
          <h3 className="text-xl font-semibold text-white truncate mb-2">{artist.name}</h3>
          {artist.genres?.length > 0 && (
            <p className="text-sm text-gray-300 mb-1">
              <span className="font-medium">Genres:</span> {artist.genres.slice(0, 2).join(', ')}
              {artist.genres.length > 2 && '...'}
            </p>
          )}
          {typeof artist.followers === 'number' && (
            <p className="text-sm text-gray-300">
              <span className="font-medium">Followers:</span> {artist.followers.toLocaleString()}
            </p>
          )}
          {typeof artist.popularity === 'number' && (
            <p className="text-sm text-gray-300">
              <span className="font-medium">Popularity:</span> {artist.popularity}
            </p>
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
  }).isRequired,
};

export default ArtistCard;
