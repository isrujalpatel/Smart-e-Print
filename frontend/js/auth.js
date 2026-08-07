/**
 * Smart e-Print — Authentication Module
 * Handles JWT storage, API calls, route guards and UI helpers.
 * Requires: config.js loaded before this file.
 */

/* ============================================================
   TOKEN & USER STORAGE
   ============================================================ */

function getToken()  { return localStorage.getItem(CONFIG.TOKEN_KEY); }
function setToken(t) { localStorage.setItem(CONFIG.TOKEN_KEY, t); }

function getStoredUser() {
  const raw = localStorage.getItem(CONFIG.USER_KEY);
  try { return raw ? JSON.parse(raw) : null; } catch { return null; }
}
function setStoredUser(u) { localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(u)); }

function clearAuth() {
  localStorage.removeItem(CONFIG.TOKEN_KEY);
  localStorage.removeItem(CONFIG.USER_KEY);
}

/* ============================================================
   LOW-LEVEL API HELPER
   ============================================================ */

/**
 * Generic fetch wrapper — attaches Bearer token when present.
 * Returns { ok, status, data }.
 */
async function apiCall(endpoint, method = 'GET', body = null) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);

  try {
    const res  = await fetch(`${CONFIG.API_BASE}${endpoint}`, opts);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return {
      ok: false, status: 0,
      data: { error: 'Network error. Is the backend running?' },
    };
  }
}

/* ============================================================
   AUTH API ACTIONS
   ============================================================ */

async function registerUser(name, email, password, role) {
  return apiCall('/auth/register', 'POST', { name, email, password, role });
}

async function loginUser(email, password) {
  return apiCall('/auth/login', 'POST', { email, password });
}

async function fetchCurrentUser() {
  return apiCall('/auth/me', 'GET');
}

function logout() {
  clearAuth();
  window.location.href = CONFIG.ROUTES.LOGIN;
}

/* ============================================================
   ROLE-BASED REDIRECT
   ============================================================ */

function redirectByRole(role) {
  if (role === 'owner') {
    window.location.href = CONFIG.ROUTES.OWNER_DASHBOARD;
  } else {
    window.location.href = CONFIG.ROUTES.CUSTOMER_DASHBOARD;
  }
}

/* ============================================================
   ROUTE GUARDS
   ============================================================ */

/**
 * requireAuth(requiredRole?)
 * - If no token → redirect to login.
 * - Fetches /auth/me to validate token with the backend.
 * - If wrong role → redirect to correct dashboard.
 * - Returns the user object on success, null otherwise.
 */
async function requireAuth(requiredRole = null) {
  if (!getToken()) { window.location.href = CONFIG.ROUTES.LOGIN; return null; }

  const { ok, data } = await fetchCurrentUser();
  if (!ok) { clearAuth(); window.location.href = CONFIG.ROUTES.LOGIN; return null; }

  const user = data.user;
  setStoredUser(user);

  if (requiredRole && user.role !== requiredRole) {
    redirectByRole(user.role); // send to their correct dashboard
    return null;
  }

  return user;
}

/**
 * redirectIfLoggedIn()
 * Call on auth pages (login/register/landing) so logged-in
 * users skip back to their dashboard automatically.
 */
function redirectIfLoggedIn() {
  const token = getToken();
  const user  = getStoredUser();
  if (token && user) redirectByRole(user.role);
}

/* ============================================================
   TOAST NOTIFICATIONS
   ============================================================ */

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.innerHTML =
    `<span class="toast-icon">${icons[type] || '●'}</span>
     <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut .3s var(--ease) forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

/* ============================================================
   FORM HELPERS
   ============================================================ */

function setLoading(btn, loading) {
  if (loading) {
    btn.dataset.txt = btn.innerHTML;
    btn.innerHTML = '<span class="btn-text" style="visibility:hidden">&nbsp;</span>';
    btn.classList.add('btn-loading');
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.txt || 'Submit';
    btn.classList.remove('btn-loading');
    btn.disabled = false;
  }
}

function showFormError(id, msg) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = 'form-alert error';
}

function hideFormAlert(id) {
  const el = document.getElementById(id);
  if (el) el.className = 'form-alert';
}

/* ============================================================
   PASSWORD TOGGLE HELPER
   ============================================================ */

function initPasswordToggle(inputId, toggleBtnId, iconId) {
  const btn   = document.getElementById(toggleBtnId);
  const input = document.getElementById(inputId);
  const icon  = document.getElementById(iconId);
  if (!btn || !input) return;
  btn.addEventListener('click', () => {
    const shown = input.type === 'text';
    input.type  = shown ? 'password' : 'text';
    if (icon) icon.className = shown ? 'bi bi-eye' : 'bi bi-eye-slash';
  });
}
