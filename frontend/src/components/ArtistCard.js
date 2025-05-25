// src/components/ArtistCard.js
import React from 'react';

function ArtistCard({ artist }) {
  const imageUrl = artist.image || 'https://via.placeholder.com/150?text=No+Image'; // Placeholder for missing images

  return (
    <a href={artist.external_urls} target="_blank" rel="noopener noreferrer" className="block transform transition-transform duration-200 hover:scale-105">
      <div className="bg-white rounded-lg shadow-md overflow-hidden flex flex-col h-full">
        <div className="relative w-full h-48 sm:h-56 md:h-64 overflow-hidden">
          <img
            src={imageUrl}
            alt={artist.name}
            className="w-full h-full object-cover"
          />
        </div>
        <div className="p-4 flex flex-col justify-between flex-grow">
          <h3 className="text-xl font-semibold text-gray-800 truncate mb-2">{artist.name}</h3>
          {artist.genres && artist.genres.length > 0 && (
            <p className="text-sm text-gray-600 mb-1">
              <span className="font-medium">Genres:</span> {artist.genres.slice(0, 2).join(', ')}
              {artist.genres.length > 2 && '...'}
            </p>
          )}
          {artist.followers !== undefined && (
            <p className="text-sm text-gray-600">
              <span className="font-medium">Followers:</span> {artist.followers.toLocaleString()}
            </p>
          )}
        </div>
      </div>
    </a>
  );
}

export default ArtistCard;