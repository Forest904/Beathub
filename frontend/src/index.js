// src/index.js
import React from 'react';
import ReactDOM from 'react-dom/client';
import axios from 'axios';
import './index.css'; // Import your global CSS (including Tailwind)
import App from './App';

axios.defaults.withCredentials = true;

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);