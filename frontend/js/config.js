/**
 * Smart e-Print — Frontend Configuration
 *
 * IMPORTANT: Vercel only hosts the static frontend (HTML/CSS/JS).
 * The Flask backend must be deployed separately (Render, Railway, etc.).
 * Once deployed, paste your backend URL below.
 */
const CONFIG = {
  // ⚠️ SET THIS to your deployed Flask backend URL (no trailing slash)
  // Local dev:  http://localhost:5000/api
  // Deployed:   https://your-backend-app.onrender.com/api
  API_BASE: window.location.hostname === 'localhost'
    ? 'http://localhost:5000/api'
    : 'http://localhost:5000/api',  // ← REPLACE with your deployed backend URL + /api

  // localStorage keys (used to cache auth state in the browser — this is normal)
  TOKEN_KEY: 'seprint_token',
  USER_KEY:  'seprint_user',

  // Page routes (relative paths)
  ROUTES: {
    LANDING:            'index.html',
    LOGIN:              'login.html',
    REGISTER:           'register.html',
    CUSTOMER_DASHBOARD: 'customer-dashboard.html',
    OWNER_DASHBOARD:    'owner-dashboard.html',
  },
};
