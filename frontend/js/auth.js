/**
 * Smart e-Print — Authentication Module
 * Handles JWT storage, API calls, route guards and UI helpers.
 * Strict 3-role routing: customer, admin, super_admin.
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

async function registerUser(name, email, password) {
  return apiCall('/auth/register', 'POST', { name, email, password });
}

async function loginUser(email, password) {
  return apiCall('/auth/login', 'POST', { email, password });
}

async function googleAuthUser(credential) {
  return apiCall('/auth/google', 'POST', { credential });
}

async function fetchCurrentUser() {
  return apiCall('/auth/me', 'GET');
}

async function logout() {
  try {
    await apiCall('/auth/logout', 'POST');
  } catch (e) {}
  clearAuth();
  window.location.href = CONFIG.ROUTES.LOGIN;
}

/* ============================================================
   ROLE-BASED REDIRECT
   ============================================================ */

function redirectByRole(role) {
  if (role === 'super_admin') {
    window.location.href = CONFIG.ROUTES.SUPER_ADMIN_DASHBOARD;
  } else if (role === 'admin' || role === 'owner') {
    window.location.href = CONFIG.ROUTES.ADMIN_DASHBOARD;
  } else {
    window.location.href = CONFIG.ROUTES.CUSTOMER_DASHBOARD;
  }
}

/* ============================================================
   ROUTE GUARDS
   ============================================================ */

/**
 * requireAuth(allowedRoles?)
 * - If no token → redirect to login.
 * - Fetches /auth/me to validate token with the backend.
 * - If user is disabled → clearAuth & redirect to login with error.
 * - If wrong role → redirect to correct dashboard.
 * - Returns the user object on success, null otherwise.
 */
async function requireAuth(allowedRoles = null) {
  if (!getToken()) {
    window.location.href = CONFIG.ROUTES.LOGIN;
    return null;
  }

  const { ok, data } = await fetchCurrentUser();
  if (!ok || !data.user) {
    clearAuth();
    window.location.href = CONFIG.ROUTES.LOGIN;
    return null;
  }

  const user = data.user;
  setStoredUser(user);

  if (user.is_active === false) {
    clearAuth();
    alert("Your account has been deactivated. Please contact an administrator.");
    window.location.href = CONFIG.ROUTES.LOGIN;
    return null;
  }

  if (allowedRoles) {
    const roles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];
    // Map legacy 'owner' to 'admin'
    const userRole = (user.role === 'owner') ? 'admin' : user.role;
    if (!roles.includes(userRole)) {
      redirectByRole(userRole);
      return null;
    }
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
  if (token && user) {
    redirectByRole(user.role);
  }
}

/* ============================================================
   TOAST NOTIFICATIONS
   ============================================================ */

function showToast(message, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    document.body.appendChild(container);
  }

  const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
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
  if (!btn) return;
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
  el.style.display = 'flex';
}

function hideFormAlert(id) {
  const el = document.getElementById(id);
  if (el) {
    el.className = 'form-alert';
    el.style.display = 'none';
  }
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
