/**
 * Smart e-Print — Frontend Configuration
 */
const CONFIG = {
  // Local dev:  http://localhost:5000/api
  // Deployed:   https://your-backend-app.onrender.com/api
  API_BASE: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:5000/api'
    : 'https://smart-e-print.onrender.com/api',

  // localStorage keys
  TOKEN_KEY: 'seprint_token',
  USER_KEY:  'seprint_user',

  // Page routes (relative paths)
  ROUTES: {
    LANDING:                'index.html',
    LOGIN:                  'login.html',
    REGISTER:               'register.html',
    CUSTOMER_DASHBOARD:     'customer-dashboard.html',
    ADMIN_DASHBOARD:        'admin-dashboard.html',
    SUPER_ADMIN_DASHBOARD:  'super-admin-dashboard.html',
    UPLOAD_PRINT:           'upload-print.html',
  },
};
