// src/components/ArtistGallery.js
import React from 'react';
import ArtistCard from './ArtistCard';

function ArtistGallery({ artists }) {
  if (!artists || artists.length === 0) {
    return (
      <div className="text-center text-gray-500 text-lg mt-8">
        No artists to display.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 p-4">
      {artists.map((artist) => (
        <ArtistCard key={artist.id} artist={artist} />
      ))}
    </div>
  );
}

export default ArtistGallery;