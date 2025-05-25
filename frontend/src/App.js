// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Header from './components/Header';
import ArtistBrowserPage from './pages/ArtistBrowserPage';
import SpotifyDownloadPage from './pages/SpotifyDownloadPage';
import ArtistDetailsPage from './pages/ArtistDetailsPage'; // Import the new page
import './App.css'; // Global styles (including Tailwind setup)

function App() {
  return (
    <Router>
      <div className="App bg-gray-100 min-h-screen">
        <Header />

        <main className="py-8">
          <Routes>
            {/* Existing routes */}
            <Route path="/artists" element={<ArtistBrowserPage />} />
            <Route path="/downloads" element={<SpotifyDownloadPage />} />

            {/* NEW ROUTE for Artist Details Page */}
            {/* The :artistId is a URL parameter that will be available via useParams() */}
            <Route path="/artists/:artistId" element={<ArtistDetailsPage />} />

            {/* Default route */}
            <Route path="/" element={<ArtistBrowserPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;