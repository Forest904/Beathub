import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Header from './components/Header';
import ArtistBrowserPage from './pages/ArtistBrowserPage';
import SpotifyDownloadPage from './pages/SpotifyDownloadPage';
import ArtistDetailsPage from './pages/ArtistDetailsPage';
import AlbumDetailsPage from './pages/AlbumDetailsPage';
import CDBurnerPage from './pages/CDBurnerPage';

const App = () => (
  <Router>
    <Header />
    <Routes>
      <Route path="/" element={<ArtistBrowserPage />} />
      <Route path="/browse" element={<ArtistBrowserPage />} />
      <Route path="/download" element={<SpotifyDownloadPage />} />
      <Route path="/artist/:artistId" element={<ArtistDetailsPage />} />
      <Route path="/album/:albumId" element={<AlbumDetailsPage />} />
      <Route path="/burn-cd" element={<CDBurnerPage />} />
    </Routes>
  </Router>
);

export default App;
