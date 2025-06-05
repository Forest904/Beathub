// frontend/src/App.js

import { BrowserRouter as Router, Routes, Route} from 'react-router-dom'; // Import useNavigate

// Import your existing pages and components
import ArtistBrowserPage from './pages/ArtistBrowserPage';
import SpotifyDownloadPage from './pages/SpotifyDownloadPage';
import ArtistDetailsPage from './pages/ArtistDetailsPage';
import AlbumDetailsPage from './pages/AlbumDetailsPage';
import Header from './components/Header';
import CDBurnerPage from './pages/CDBurnerPage';

function App() {

    return (
        <div className="App">
            <Router>
                <Header /> {/* Header is part of your main layout, and might contain <Link> components */}

                <Routes>
                    <Route path="/" element={<ArtistBrowserPage />} />
                    <Route path="/browse" element={<ArtistBrowserPage />} />
                    <Route path="/download" element={<SpotifyDownloadPage />} />
                    <Route path="/artist/:artistId" element={<ArtistDetailsPage />} />
                    <Route path="/album/:albumId" element={<AlbumDetailsPage />} />
                    <Route path="/burn-cd" element={<CDBurnerPage />} />
                </Routes>
            </Router>
        </div>
    );
}

export default App;