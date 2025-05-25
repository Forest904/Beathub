// src/App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Header from './components/Header'; // New Header component
import ArtistBrowserPage from './pages/ArtistBrowserPage'; // Your new artist page
import SpotifyDownloadPage from './pages/SpotifyDownloadPage'; // Your renamed App.js
import './App.css'; // Global styles (including Tailwind setup)

function App() {
  return (
    <Router>
      <div className="App bg-gray-100 min-h-screen">
        <Header /> {/* Render the Header here */}

        <main className="py-8"> {/* Add some padding to main content */}
          <Routes>
            {/* Define your routes */}
            <Route path="/artists" element={<ArtistBrowserPage />} />
            <Route path="/downloads" element={<SpotifyDownloadPage />} />
            {/* Set a default route, e.g., redirect to artists or downloads */}
            <Route path="/" element={<ArtistBrowserPage />} /> {/* Default to Artist Browser */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;