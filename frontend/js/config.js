/**
 * Smart e-Print — Frontend Configuration
 * Change API_BASE when deploying to Render.
 */
const CONFIG = {
  // Local dev: http://localhost:5000/api
  // Render:    https://your-app.onrender.com/api
  API_BASE: 'http://localhost:5000/api',

  // localStorage keys
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
