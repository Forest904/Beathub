import React from 'react';
import PropTypes from 'prop-types';
import ArtistCard from './ArtistCard';

const ArtistGallery = ({ artists }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
    {artists.map((artist) => (
      <ArtistCard key={artist.id} artist={artist} />
    ))}
  </div>
);

ArtistGallery.propTypes = {
  artists: PropTypes.arrayOf(ArtistCard.propTypes.artist).isRequired,
};

export default ArtistGallery;
