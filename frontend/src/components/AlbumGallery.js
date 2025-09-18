import React from 'react';
import PropTypes from 'prop-types';
import AlbumCard, { AlbumCardVariant } from './AlbumCard';

const AlbumGallery = ({ albums, onDelete, onSelect, variant, selectedAlbumId, disabled }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
    {albums.map((album) => (
      <AlbumCard
        key={album.id}
        album={album}
        onDelete={onDelete}
        onSelect={onSelect}
        variant={variant}
        isSelected={selectedAlbumId === album.id}
        disabled={disabled}
      />
    ))}
  </div>
);

AlbumGallery.propTypes = {
  albums: PropTypes.arrayOf(AlbumCard.propTypes.album).isRequired,
  onDelete: PropTypes.func,
  onSelect: PropTypes.func,
  variant: PropTypes.oneOf(Object.values(AlbumCardVariant)),
  selectedAlbumId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  disabled: PropTypes.bool,
};

AlbumGallery.defaultProps = {
  onDelete: undefined,
  onSelect: undefined,
  variant: AlbumCardVariant.DISCOVERY,
  selectedAlbumId: undefined,
  disabled: false,
};

export default AlbumGallery;
