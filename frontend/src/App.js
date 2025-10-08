import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Header from './shared/components/Header';
import Footer from './shared/components/Footer';
import ArtistBrowserPage from './features/catalog/pages/ArtistBrowserPage';
import ArtistDetailsPage from './features/catalog/pages/ArtistDetailsPage';
import AlbumDetailsPage from './features/catalog/pages/AlbumDetailsPage';
import DownloadPage from './features/downloads/pages/DownloadPage';
import CDBurnerPage from './features/burner/pages/CDBurnerPage';
import { ThemeProvider } from './theme/ThemeContext';
import { PlayerProvider } from './player/PlayerContext';
import { AuthProvider } from './shared/hooks/useAuth';
import PlayerBar from './shared/components/PlayerBar.jsx';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import MyPlaylistsPage from './features/playlists/pages/MyPlaylistsPage.jsx';
import FavoritesPage from './features/favorites/pages/FavoritesPage.jsx';

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <ThemeProvider>
        <PlayerProvider>
          <Router>
            <div className="flex min-h-screen flex-col bg-brand-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
              <Header />
              <main className="flex-1 bg-white text-slate-900 dark:bg-slate-900 dark:text-slate-100">
                <Routes>
                  <Route path="/" element={<ArtistBrowserPage />} />
                  <Route path="/browse" element={<ArtistBrowserPage />} />
                  <Route path="/download" element={<DownloadPage />} />
                  <Route path="/playlists" element={<MyPlaylistsPage />} />
                  <Route path="/favorites" element={<FavoritesPage />} />
                  <Route path="/artist/:artistId" element={<ArtistDetailsPage />} />
                  <Route path="/album/:albumId" element={<AlbumDetailsPage />} />
                  <Route path="/burn-cd" element={<CDBurnerPage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                </Routes>
              </main>
              <Footer />
            </div>
          </Router>
          <PlayerBar />
        </PlayerProvider>
      </ThemeProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
