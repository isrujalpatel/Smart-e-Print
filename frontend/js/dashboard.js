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
  await fetchDashRates();
  const user = await requireAuth(requiredRole);
  if (!user) return null;

  // ── Sidebar user info ─────────────────────────────────────────────────────
  const nameEl   = document.getElementById('sidebarUserName');
  const roleEl   = document.getElementById('sidebarUserRoleLabel');
  const avatarEl = document.getElementById('sidebarAvatar');

  if (nameEl)   nameEl.textContent   = user.name;
  if (roleEl)   roleEl.textContent   = user.role.charAt(0).toUpperCase() + user.role.slice(1).replace('_', ' ');
  if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();

  // ── Welcome greeting ──────────────────────────────────────────────────────
  const welcomeEl = document.getElementById('welcomeName');
  if (welcomeEl) welcomeEl.textContent = user.name.split(' ')[0];

  // ── Logout button ─────────────────────────────────────────────────────────
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', (e) => { e.preventDefault(); logout(); });
  }

  // If on customer dashboard, load order history and stats
  if (user.role === 'customer' && document.getElementById('custOrdersTableBody')) {
    loadCustomerOrders();
  }

  return user;
}

async function fetchDashRates() {
  try {
    const { ok, data } = await apiCall('/shop/rates', 'GET');
    if (ok && data) {
      if (data.PRICE_RATES) DASH_PRICE_RATES = data.PRICE_RATES;
      if (data.PAPER_MULTIPLIERS) DASH_PAPER_MULTIPLIERS = data.PAPER_MULTIPLIERS;
    }
  } catch (err) {
    console.warn("Could not fetch latest rates on dashboard.");
  }
}

/**
 * Load and render customer's own print orders & stats
 */
async function loadCustomerOrders() {
  const tbody = document.getElementById('custOrdersTableBody');
  if (!tbody) return;

  const { ok, data } = await apiCall('/orders', 'GET');
  if (!ok) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load orders.</td></tr>`;
    return;
  }

  const orders = data.orders || [];

  // Update customer stats
  const totalOrdersEl = document.getElementById('custStatTotal');
  const completedEl = document.getElementById('custStatCompleted');
  const pendingEl = document.getElementById('custStatPending');
  const spentEl = document.getElementById('custStatSpent');

  const completedCount = orders.filter(o => o.status === 'Completed').length;
  const pendingCount = orders.filter(o => ['Submitted', 'Accepted', 'Printing'].includes(o.status)).length;
  const totalSpent = orders.reduce((sum, o) => sum + (o.status !== 'Rejected' ? o.total_price : 0), 0);

  if (totalOrdersEl) totalOrdersEl.textContent = orders.length;
  if (completedEl) completedEl.textContent = completedCount;
  if (pendingEl) pendingEl.textContent = pendingCount;
  if (spentEl) spentEl.textContent = `₹${totalSpent.toFixed(2)}`;

  if (orders.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No print orders submitted yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = orders.map(o => {
    const shortId = o.id.substring(0, 8);
    const dateStr = o.created_at ? new Date(o.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
    const modeBadge = o.print_mode === 'color' ? '<span class="badge bg-warning text-dark">Color</span>' : '<span class="badge bg-secondary">B&W</span>';
    
    return `
      <tr>
        <td><span class="font-monospace text-info small">#${shortId}</span></td>
        <td>
          <div class="fw-bold text-truncate" style="max-width:180px;" title="${escapeHtml(o.file_name)}">
            <i class="bi bi-file-earmark-pdf me-1 text-danger"></i>${escapeHtml(o.file_name)}
          </div>
          <small class="text-muted">${(o.file_size / (1024*1024)).toFixed(2)} MB</small>
        </td>
        <td>${modeBadge} <small class="text-muted">· ${o.paper_size || 'A4'}</small></td>
        <td>
          <div>${o.copies} ${o.copies > 1 ? 'copies' : 'copy'}</div>
          <small class="text-muted">${o.printed_pages} pages</small>
        </td>
        <td><strong class="text-success">₹${o.total_price.toFixed(2)}</strong></td>
        <td>
          <span class="order-status-badge status-${o.status}">● ${o.status}</span>
          ${o.rejection_reason ? `<div class="small text-danger mt-1 text-truncate" style="max-width:140px;" title="${escapeHtml(o.rejection_reason)}">Reason: ${escapeHtml(o.rejection_reason)}</div>` : ''}
        </td>
        <td><small class="text-muted">${dateStr}</small></td>
      </tr>
    `;
  }).join('');
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── DASHBOARD UPLOAD FEATURE ────────────────────────────────────────────────
const DASH_UPLOAD_MAX = 10 * 1024 * 1024;
let DASH_PRICE_RATES = { bw: 2.0, color: 5.0 };
let DASH_PAPER_MULTIPLIERS = { A4: 1.0, A3: 1.25, Letter: 1.1 };

let dashUploadedFiles = [];
let dashActiveFileId = null;
let dashFileCounter = 0;
let dashConfigModal = null;

document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.getElementById('dashFileInput');
  if (!fileInput) return; // Not on customer dashboard

  // Initialize Modal
  dashConfigModal = new bootstrap.Modal(document.getElementById('configModal'), {
    backdrop: 'static'
  });

  fileInput.addEventListener('change', handleDashFileSelection);
  document.getElementsByName('dashRangeModeToggle').forEach(radio => {
    radio.addEventListener('change', handleDashRangeSwitch);
  });
  
  document.getElementById('dashCopiesInput').addEventListener('input', (e) => {
    const file = getDashActiveFile();
    if (file) {
      file.copies = Math.max(1, Number(e.target.value) || 1);
      renderDashSummary();
    }
  });
  
  document.getElementById('dashPaperSizeSelect').addEventListener('change', (e) => {
    const file = getDashActiveFile();
    if (file) {
      file.paperSize = e.target.value;
      renderDashSummary();
    }
  });
  
  document.getElementById('dashPageRangeInput').addEventListener('input', (e) => {
    const file = getDashActiveFile();
    if (file) {
      file.pageRange = e.target.value;
      renderDashSummary();
    }
  });
  
  document.getElementsByName('dashPrintMode').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const file = getDashActiveFile();
      if (file) {
        file.printMode = e.target.value;
        renderDashSummary();
      }
    });
  });

  document.getElementById('dashSubmitOrderBtn').addEventListener('click', handleDashSubmitOrder);
});

function getDashActiveFile() {
  return dashUploadedFiles.find(f => f.id === dashActiveFileId);
}

function handleDashRangeSwitch(event) {
  const file = getDashActiveFile();
  if (file) {
    file.rangeMode = event.target.value;
    if (file.rangeMode !== 'custom') file.pageRange = '';
  }
  renderDashConfigPanel();
  renderDashSummary();
}

async function handleDashFileSelection() {
  const fileInput = document.getElementById('dashFileInput');
  const files = Array.from(fileInput.files);
  if (files.length === 0) return;

  let added = false;
  for (const file of files) {
    if (file.size > DASH_UPLOAD_MAX) {
      if(typeof showToast === 'function') showToast(`File ${file.name} is larger than 10MB.`);
      continue;
    }
    if (!['application/pdf', 'image/png', 'image/jpeg'].includes(file.type)) {
      if(typeof showToast === 'function') showToast(`File ${file.name} is not a supported format.`);
      continue;
    }

    const pageCount = await getDashPageCount(file);
    dashUploadedFiles.push({
      id: `d_file_${dashFileCounter++}`,
      fileObj: file,
      name: file.name,
      type: file.type,
      size: file.size,
      pages: pageCount,
      printMode: 'bw',
      copies: 1,
      paperSize: 'A4',
      rangeMode: 'full',
      pageRange: ''
    });
    added = true;
  }
  fileInput.value = '';

  if (added) {
    if (!dashActiveFileId) dashActiveFileId = dashUploadedFiles[0].id;
    renderDashFileList();
    renderDashConfigPanel();
    renderDashSummary();
    dashConfigModal.show();
  }
}

function getDashPageCount(file) {
  return new Promise((resolve) => {
    if (file.type !== 'application/pdf') { resolve(1); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const text = new TextDecoder('latin1').decode(reader.result);
      const matches = text.match(/\/Type\s*\/Page\b/g);
      resolve(matches ? matches.length : 1);
    };
    reader.readAsArrayBuffer(file);
  });
}

function formatDashBytes(bytes) {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function renderDashFileList() {
  const container = document.getElementById('dashFileListContainer');
  const addBtn = document.getElementById('dashAddMoreFilesBtn');
  container.innerHTML = '';
  
  if (dashUploadedFiles.length === 0) {
    if (addBtn) addBtn.style.display = 'none';
    dashConfigModal.hide();
    return;
  }
  
  if (addBtn) addBtn.style.display = 'flex';

  dashUploadedFiles.forEach(f => {
    const el = document.createElement('div');
    el.className = `file-list-item ${f.id === dashActiveFileId ? 'active' : ''}`;
    el.onclick = () => {
      dashActiveFileId = f.id;
      renderDashFileList();
      renderDashConfigPanel();
      renderDashSummary();
    };

    el.innerHTML = `
      <div class="file-info-wrap">
        <div class="file-list-name" title="${f.name}">${f.name}</div>
        <div class="file-list-meta">
          <span>${f.pages} page${f.pages > 1 ? 's' : ''}</span>
          <span>${formatDashBytes(f.size)}</span>
        </div>
      </div>
      <button class="btn-remove-file" title="Remove file" data-id="${f.id}">
        <i class="bi bi-x-lg"></i>
      </button>
    `;

    el.querySelector('.btn-remove-file').onclick = (e) => {
      e.stopPropagation();
      dashUploadedFiles = dashUploadedFiles.filter(item => item.id !== f.id);
      if (dashActiveFileId === f.id) {
        dashActiveFileId = dashUploadedFiles.length > 0 ? dashUploadedFiles[0].id : null;
      }
      renderDashFileList();
      renderDashConfigPanel();
      renderDashSummary();
    };
    container.appendChild(el);
  });
}

function renderDashConfigPanel() {
  const emptyState = document.getElementById('dashConfigPanelEmpty');
  const formPanel = document.getElementById('dashConfigPanelForm');
  const file = getDashActiveFile();

  if (!file) {
    emptyState.style.display = 'block';
    formPanel.style.display = 'none';
    return;
  }
  emptyState.style.display = 'none';
  formPanel.style.display = 'block';

  const printModeInput = document.querySelector(`input[name="dashPrintMode"][value="${file.printMode}"]`);
  if (printModeInput) {
    printModeInput.checked = true;
  }
  document.getElementById('dashCopiesInput').value = file.copies;
  document.getElementById('dashPaperSizeSelect').value = file.paperSize || '';
  
  const rangeRadios = document.getElementsByName('dashRangeModeToggle');
  rangeRadios.forEach((r) => r.checked = (r.value === file.rangeMode));

  const customContainer = document.getElementById('dashCustomRangeContainer');
  const customInput = document.getElementById('dashPageRangeInput');
  if (file.rangeMode === 'custom') {
    customContainer.style.display = 'block';
  } else {
    customContainer.style.display = 'none';
  }
  customInput.value = file.pageRange;
}

function parseDashPageRange(rangeText, maxPages) {
  if (!rangeText || !rangeText.trim()) return { count: maxPages, error: null };
  const pages = new Set();
  const parts = rangeText.split(',').map((part) => part.trim()).filter(Boolean);
  for (const part of parts) {
    if (/^\d+$/.test(part)) {
      const page = Number(part);
      if (!page || page < 1 || page > maxPages) return { count: 0, error: `Page values must be between 1 and ${maxPages}.` };
      pages.add(page);
    } else if (/^\d+-\d+$/.test(part)) {
      const [start, end] = part.split('-').map(Number);
      if (start < 1 || end < start || end > maxPages) return { count: 0, error: `Ranges must fall between 1 and ${maxPages}.` };
      for (let p = start; p <= end; p += 1) pages.add(p);
    } else {
      return { count: 0, error: 'Use a valid page range.' };
    }
  }
  return { count: pages.size, error: null };
}

function calculateDashFileCost(file) {
  if (!file) return 0;
  let selectedPages = file.pages;
  if (file.rangeMode === 'custom') {
    const parsed = parseDashPageRange(file.pageRange, file.pages || 1);
    selectedPages = parsed.count;
  }
  if (file.pages === 0) selectedPages = 0;
  
  const rate = DASH_PRICE_RATES[file.printMode] || DASH_PRICE_RATES.bw;
  const multiplier = DASH_PAPER_MULTIPLIERS[file.paperSize] || 1.0;
  return selectedPages * file.copies * rate * multiplier;
}

function renderDashSummary() {
  const file = getDashActiveFile();
  const submitBtn = document.getElementById('dashSubmitOrderBtn');
  
  let grandTotal = 0;
  let hasErrors = false;
  
  for (const f of dashUploadedFiles) {
    grandTotal += calculateDashFileCost(f);
    if (f.rangeMode === 'custom') {
      const parsed = parseDashPageRange(f.pageRange, f.pages);
      if (parsed.error || parsed.count < 1) hasErrors = true;
    }
    if (f.pages === 0) hasErrors = true;
  }
  
  if (file) {
    let selectedPages = file.pages;
    if (file.rangeMode === 'custom') {
      const parsed = parseDashPageRange(file.pageRange, file.pages || 1);
      selectedPages = parsed.count;
    }
    if (file.pages === 0) selectedPages = 0;
    
    document.getElementById('dashSummaryPageCount').textContent = file.pages || '0';
    document.getElementById('dashSummarySelectedPages').textContent = selectedPages || '0';
    document.getElementById('dashSummaryCopies').textContent = file.copies;
    document.getElementById('dashSummaryMode').textContent = file.printMode === 'color' ? 'Color' : 'B&W';
    document.getElementById('dashSummaryPaperSize').textContent = file.paperSize || 'A4';
    
    const activeCost = calculateDashFileCost(file);
    document.getElementById('dashSummaryTotal').textContent = `₹${activeCost.toFixed(2)}`;
  } else {
    document.getElementById('dashSummaryPageCount').textContent = '0';
    document.getElementById('dashSummarySelectedPages').textContent = '0';
    document.getElementById('dashSummaryCopies').textContent = '1';
    document.getElementById('dashSummaryMode').textContent = 'B&W';
    document.getElementById('dashSummaryPaperSize').textContent = 'A4';
    document.getElementById('dashSummaryTotal').textContent = '₹0.00';
  }

  document.getElementById('dashGrandTotal').textContent = `₹${grandTotal.toFixed(2)}`;
  submitBtn.disabled = dashUploadedFiles.length === 0 || hasErrors;
}

async function handleDashSubmitOrder() {
  if (dashUploadedFiles.length === 0) return;
  const button = document.getElementById('dashSubmitOrderBtn');
  button.disabled = true;
  button.textContent = 'Submitting…';

  try {
    for (const file of dashUploadedFiles) {
      const formData = new FormData();
      formData.append('file', file.fileObj);
      formData.append('print_mode', file.printMode);
      formData.append('copies', file.copies);
      formData.append('range_type', file.rangeMode);
      formData.append('page_range', file.pageRange);
      formData.append('paper_size', file.paperSize);

      const paymentMethod = document.querySelector('input[name="dashPaymentMethod"]:checked')?.value || 'cash';
      formData.append('payment_method', paymentMethod);

      const response = await fetch(`${CONFIG.API_BASE}/orders`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Failed to submit file: ${file.name}`);
      }
    }

    dashUploadedFiles = [];
    dashActiveFileId = null;
    document.getElementById('dashFileInput').value = '';
    
    dashConfigModal.hide();
    if(typeof showToast === 'function') showToast('Orders submitted successfully!');
    if(typeof loadCustomerOrders === 'function') loadCustomerOrders();
  } catch (err) {
    if(typeof showToast === 'function') showToast(err.message || 'Network error. Please try again.');
  } finally {
    if (dashUploadedFiles.length > 0) button.disabled = false;
    button.textContent = 'Submit Order';
  }
}
