/**
 * Smart e-Print — Dashboard Module
 * Initializes protected dashboard pages: verifies auth, populates UI, sets up logout.
 * Requires: config.js and auth.js loaded first.
 */

/**
 * initDashboard(requiredRole)
 * Call once per dashboard page on DOMContentLoaded.
 * Returns the authenticated user object, or null (and redirects) on failure.
 */
async function initDashboard(requiredRole) {
  const user = await requireAuth(requiredRole);
  if (!user) return null;

  // ── Sidebar user info ─────────────────────────────────────────────────────
  const nameEl   = document.getElementById('sidebarUserName');
  const roleEl   = document.getElementById('sidebarUserRoleLabel');
  const avatarEl = document.getElementById('sidebarAvatar');

  if (nameEl)   nameEl.textContent   = user.name;
  if (roleEl)   roleEl.textContent   = user.role.charAt(0).toUpperCase() + user.role.slice(1);
  if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();

  // ── Welcome greeting ──────────────────────────────────────────────────────
  const welcomeEl = document.getElementById('welcomeName');
  if (welcomeEl) welcomeEl.textContent = user.name.split(' ')[0];

  // ── Logout button ─────────────────────────────────────────────────────────
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => { e.preventDefault(); logout(); });
  }

  return user;
}
