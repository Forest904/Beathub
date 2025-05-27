// src/components/ArtistCard.js
import React from 'react';
import { Link } from 'react-router-dom';

function ArtistCard({ artist }) {
  const imageUrl = artist.image || 'https://via.placeholder.com/150?text=No+Image'; // Placeholder for missing images

  return (
    // Use Link component for navigation
    <Link
      to={`/artist/${artist.id}`}
      className="block transform transition-transform duration-200 hover:scale-105"
    >
      {/* Changed background to dark gray (bg-gray-800) */}
      <div className="bg-gray-800 rounded-lg shadow-md overflow-hidden flex flex-col h-full">
        <div className="relative w-full h-48 sm:h-56 md:h-64 overflow-hidden">
          <img
            src={imageUrl}
            alt={artist.name}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="p-4 flex flex-col justify-between flex-grow">
          {/* Changed text color to white */}
          <h3 className="text-xl font-semibold text-white truncate mb-2">{artist.name}</h3>
          {artist.genres && artist.genres.length > 0 && (
            <p className="text-sm text-gray-300 mb-1"> {/* Changed text color to lighter gray */}
              <span className="font-medium">Genres:</span> {artist.genres.slice(0, 2).join(', ')}
              {artist.genres.length > 2 && '...'}
            </p>
          )}
          {artist.followers !== undefined && (
            <p className="text-sm text-gray-300"> {/* Changed text color to lighter gray */}
              <span className="font-medium">Followers:</span> {artist.followers.toLocaleString()}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}

export default ArtistCard;