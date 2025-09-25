import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import ArtistBrowserPage from './pages/ArtistBrowserPage';
import SpotifyDownloadPage from './pages/SpotifyDownloadPage';
import ArtistDetailsPage from './pages/ArtistDetailsPage';
import AlbumDetailsPage from './pages/AlbumDetailsPage';
import CDBurnerPage from './pages/CDBurnerPage';
import { ThemeProvider } from './theme/ThemeContext';
import { PlayerProvider } from './player/PlayerContext';
import { CompilationProvider } from './compilation/CompilationContext.jsx';
import { AuthProvider } from './hooks/useAuth';
import CompilationSidebar from './compilation/CompilationSidebar.jsx';
import PlayerBar from './components/PlayerBar';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

const App = () => (
  <AuthProvider>
    <ThemeProvider>
      <PlayerProvider>
        <CompilationProvider>
          <Router>
            <div className="flex min-h-screen flex-col bg-brand-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
              <Header />
              <main className="flex-1 bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
                <Routes>
                  <Route path="/" element={<ArtistBrowserPage />} />
                  <Route path="/browse" element={<ArtistBrowserPage />} />
                  <Route path="/download" element={<SpotifyDownloadPage />} />
                  <Route path="/artist/:artistId" element={<ArtistDetailsPage />} />
                  <Route path="/album/:albumId" element={<AlbumDetailsPage />} />
                  <Route path="/burn-cd" element={<CDBurnerPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                </Routes>
              </main>
              <Footer />
            </div>
            <CompilationSidebar />
          </Router>
          <PlayerBar />
        </CompilationProvider>
      </PlayerProvider>
    </ThemeProvider>
  </AuthProvider>
);

export default App;
