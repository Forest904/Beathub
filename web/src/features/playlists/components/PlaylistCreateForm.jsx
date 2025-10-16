import React, { useState } from 'react';
import PropTypes from 'prop-types';

const PlaylistCreateForm = ({ onCreate, isSubmitting }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Give your playlist a name before saving.');
      return;
    }
    setError('');
    await onCreate({
      name: trimmedName,
      description: description.trim() || null,
    });
    setName('');
    setDescription('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-2xl bg-white p-6 shadow ring-1 ring-brand-100 dark:bg-gray-900 dark:ring-gray-700"
    >
      <div>
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-white">
          Create a new playlist
        </h2>
        <p className="text-sm text-slate-600 dark:text-gray-400">
          Organise your favourite tracks into a personal collection.
        </p>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="playlist-name">
          Name
        </label>
        <input
          id="playlist-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
          placeholder="Road trip mix"
          disabled={isSubmitting}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700 dark:text-gray-300" htmlFor="playlist-description">
          Description
        </label>
        <textarea
          id="playlist-description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          rows={3}
          className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100"
          placeholder="A set of songs to keep me energised on long drives"
          disabled={isSubmitting}
        />
      </div>
      {error && <p className="text-sm text-brandError-600 dark:text-brandError-400">{error}</p>}
      <button
        type="submit"
        className="rounded-full bg-brand-600 px-4 py-2 font-medium text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-brandDark-500 dark:hover:bg-brandDark-400"
        disabled={isSubmitting}
      >
        {isSubmitting ? 'Creating…' : 'Create playlist'}
      </button>
    </form>
  );
};

PlaylistCreateForm.propTypes = {
  onCreate: PropTypes.func.isRequired,
  isSubmitting: PropTypes.bool,
};

PlaylistCreateForm.defaultProps = {
  isSubmitting: false,
};

export default PlaylistCreateForm;
