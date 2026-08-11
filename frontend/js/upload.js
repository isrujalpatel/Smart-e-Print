/**
 * Smart e-Print — Upload + Print Configuration
 * Requires: config.js, auth.js, dashboard.js loaded before this file.
 */
const UPLOAD_MAX_BYTES = 10 * 1024 * 1024;
const PRICE_RATES = { bw: 2.0, color: 5.0 };
const PAPER_MULTIPLIERS = { A4: 1.0, A3: 1.25, Letter: 1.1 };

let uploadedFiles = [];
let activeFileId = null;
let fileIdCounter = 0;

function initUploadPage() {
  const fileInput = document.getElementById('fileInput');
  const submitBtn = document.getElementById('submitOrderBtn');

  if (!fileInput || !submitBtn) return;

  fileInput.addEventListener('change', handleFileSelection);
  document.getElementsByName('rangeModeToggle').forEach(radio => {
    radio.addEventListener('change', handleRangeSwitch);
  });
  
  document.getElementById('copiesInput').addEventListener('input', (e) => {
    const file = getActiveFile();
    if (file) {
      file.copies = Math.max(1, Number(e.target.value) || 1);
      renderSummary();
    }
  });
  
  document.getElementById('paperSizeSelect').addEventListener('change', (e) => {
    const file = getActiveFile();
    if (file) {
      file.paperSize = e.target.value;
      renderSummary();
    }
  });
  
  document.getElementById('pageRangeInput').addEventListener('input', (e) => {
    const file = getActiveFile();
    if (file) {
      file.pageRange = e.target.value;
      renderSummary();
    }
  });
  
  document.getElementsByName('printMode').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      const file = getActiveFile();
      if (file) {
        file.printMode = e.target.value;
        renderSummary();
      }
    });
  });

  submitBtn.addEventListener('click', handleSubmitOrder);
  renderSummary();
}

function getActiveFile() {
  return uploadedFiles.find(f => f.id === activeFileId);
}

function setAlert(message, type = 'error') {
  const alert = document.getElementById('formAlert');
  if (!alert) return;
  alert.textContent = message;
  alert.className = `form-alert ${type}`;
  alert.style.display = 'flex';
}

function clearAlert() {
  const alert = document.getElementById('formAlert');
  if (!alert) return;
  alert.textContent = '';
  alert.className = 'form-alert';
  alert.style.display = 'none';
}

function handleRangeSwitch(event) {
  const file = getActiveFile();
  if (file) {
    file.rangeMode = event.target.value;
    if (file.rangeMode !== 'custom') file.pageRange = '';
  }
  renderConfigPanel();
  renderSummary();
}

async function handleFileSelection() {
  clearAlert();
  const fileInput = document.getElementById('fileInput');
  const files = Array.from(fileInput.files);
  if (files.length === 0) return;

  for (const file of files) {
    if (file.size > UPLOAD_MAX_BYTES) {
      setAlert(`File ${file.name} is larger than 10MB.`);
      continue;
    }

    if (!['application/pdf', 'image/png', 'image/jpeg'].includes(file.type)) {
      setAlert(`File ${file.name} is not a supported format.`);
      continue;
    }

    const pageCount = await getPageCount(file);
    const newFile = {
      id: `file_${fileIdCounter++}`,
      fileObj: file,
      name: file.name,
      type: file.type,
      size: file.size,
      pages: pageCount,
      // Default Config
      printMode: 'bw',
      copies: 1,
      paperSize: 'A4',
      rangeMode: 'full',
      pageRange: ''
    };

    uploadedFiles.push(newFile);
  }

  // Clear input so we can upload the same file again if needed
  fileInput.value = '';

  if (uploadedFiles.length > 0 && !activeFileId) {
    activeFileId = uploadedFiles[0].id;
  }

  renderFileList();
  renderConfigPanel();
  renderSummary();
}

function getPageCount(file) {
  return new Promise((resolve) => {
    if (file.type !== 'application/pdf') {
      resolve(1);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const text = new TextDecoder('latin1').decode(reader.result);
      const matches = text.match(/\/Type\s*\/Page\b/g);
      resolve(matches ? matches.length : 1);
    };
    reader.readAsArrayBuffer(file);
  });
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function renderFileList() {
  const container = document.getElementById('fileListContainer');
  const addBtn = document.getElementById('addMoreFilesBtn');
  if (uploadedFiles.length === 0) {
    container.style.display = 'none';
    if (addBtn) addBtn.style.display = 'none';
    container.innerHTML = '';
    return;
  }

  container.style.display = 'flex';
  if (addBtn) addBtn.style.display = 'flex';
  container.innerHTML = '';

  uploadedFiles.forEach(f => {
    const el = document.createElement('div');
    el.className = `file-list-item ${f.id === activeFileId ? 'active' : ''}`;
    el.onclick = () => {
      activeFileId = f.id;
      renderFileList();
      renderConfigPanel();
      renderSummary();
    };

    el.innerHTML = `
      <div class="file-info-wrap">
        <div class="file-list-name" title="${f.name}">${f.name}</div>
        <div class="file-list-meta">
          <span>${f.pages} page${f.pages > 1 ? 's' : ''}</span>
          <span>${formatBytes(f.size)}</span>
        </div>
      </div>
      <button class="btn-remove-file" title="Remove file" data-id="${f.id}">
        <i class="bi bi-x-lg"></i>
      </button>
    `;

    // Remove file logic
    const removeBtn = el.querySelector('.btn-remove-file');
    removeBtn.onclick = (e) => {
      e.stopPropagation();
      uploadedFiles = uploadedFiles.filter(item => item.id !== f.id);
      if (activeFileId === f.id) {
        activeFileId = uploadedFiles.length > 0 ? uploadedFiles[0].id : null;
      }
      renderFileList();
      renderConfigPanel();
      renderSummary();
    };

    container.appendChild(el);
  });
}

function renderConfigPanel() {
  const emptyState = document.getElementById('configPanelEmpty');
  const formPanel = document.getElementById('configPanelForm');
  const file = getActiveFile();

  if (!file) {
    emptyState.style.display = 'block';
    formPanel.style.display = 'none';
    return;
  }

  emptyState.style.display = 'none';
  formPanel.style.display = 'block';

  // Apply active file config to form
  const printModeInput = document.querySelector(`input[name="printMode"][value="${file.printMode}"]`);
  if (printModeInput) {
    printModeInput.checked = true;
  }
  document.getElementById('copiesInput').value = file.copies;
  document.getElementById('paperSizeSelect').value = file.paperSize || '';
  
  const rangeRadios = document.getElementsByName('rangeModeToggle');
  rangeRadios.forEach((r) => r.checked = (r.value === file.rangeMode));

  const customContainer = document.getElementById('customRangeContainer');
  const customInput = document.getElementById('pageRangeInput');
  if (file.rangeMode === 'custom') {
    customContainer.style.display = 'block';
  } else {
    customContainer.style.display = 'none';
  }
  customInput.value = file.pageRange;
}

function parsePageRange(rangeText, maxPages) {
  if (!rangeText || !rangeText.trim()) {
    return { count: maxPages, error: null };
  }

  const pages = new Set();
  const parts = rangeText.split(',').map((part) => part.trim()).filter(Boolean);
  for (const part of parts) {
    if (/^\d+$/.test(part)) {
      const page = Number(part);
      if (!page || page < 1 || page > maxPages) {
        return { count: 0, error: `Page values must be between 1 and ${maxPages}.` };
      }
      pages.add(page);
    } else if (/^\d+-\d+$/.test(part)) {
      const [start, end] = part.split('-').map(Number);
      if (start < 1 || end < start || end > maxPages) {
        return { count: 0, error: `Ranges must fall between 1 and ${maxPages}.` };
      }
      for (let p = start; p <= end; p += 1) pages.add(p);
    } else {
      return { count: 0, error: 'Use a valid page range like 1-3, 5, 8-10.' };
    }
  }

  return { count: pages.size, error: null };
}

function calculateFileCost(file) {
  if (!file) return 0;
  
  let selectedPages = file.pages;
  if (file.rangeMode === 'custom') {
    const parsed = parsePageRange(file.pageRange, file.pages || 1);
    selectedPages = parsed.count;
  }
  
  if (file.pages === 0) selectedPages = 0;
  
  const rate = PRICE_RATES[file.printMode] || PRICE_RATES.bw;
  const multiplier = PAPER_MULTIPLIERS[file.paperSize] || 1.0;
  return selectedPages * file.copies * rate * multiplier;
}

function renderSummary() {
  const file = getActiveFile();
  const submitBtn = document.getElementById('submitOrderBtn');
  
  let grandTotal = 0;
  let hasErrors = false;
  let activeError = null;
  
  // Calculate grand total and check errors across all files
  for (const f of uploadedFiles) {
    const cost = calculateFileCost(f);
    grandTotal += cost;
    
    if (f.rangeMode === 'custom') {
      const parsed = parsePageRange(f.pageRange, f.pages);
      if (parsed.error || parsed.count < 1) {
        hasErrors = true;
        if (f.id === activeFileId) activeError = parsed.error || 'Select at least one page to print.';
      }
    }
    if (f.pages === 0) {
      hasErrors = true;
      if (f.id === activeFileId) activeError = 'Invalid document pages.';
    }
  }
  
  // Update UI for active file
  if (file) {
    let selectedPages = file.pages;
    if (file.rangeMode === 'custom') {
      const parsed = parsePageRange(file.pageRange, file.pages || 1);
      selectedPages = parsed.count;
    }
    if (file.pages === 0) selectedPages = 0;
    
    document.getElementById('summaryPageCount').textContent = file.pages || '0';
    document.getElementById('summarySelectedPages').textContent = selectedPages || '0';
    document.getElementById('summaryCopies').textContent = file.copies;
    document.getElementById('summaryMode').textContent = file.printMode === 'color' ? 'Color' : 'B&W';
    document.getElementById('summaryPaperSize').textContent = file.paperSize || 'A4';
    
    const activeCost = calculateFileCost(file);
    document.getElementById('summaryTotal').textContent = `₹${activeCost.toFixed(2)}`;
  } else {
    document.getElementById('summaryPageCount').textContent = '0';
    document.getElementById('summarySelectedPages').textContent = '0';
    document.getElementById('summaryCopies').textContent = '1';
    document.getElementById('summaryMode').textContent = 'B&W';
    document.getElementById('summaryPaperSize').textContent = 'A4';
    document.getElementById('summaryTotal').textContent = '₹0.00';
  }

  // Update Grand Total
  document.getElementById('grandTotal').textContent = `₹${grandTotal.toFixed(2)}`;
  
  if (activeError) {
    setAlert(activeError, 'error');
  } else {
    clearAlert();
  }
  
  submitBtn.disabled = uploadedFiles.length === 0 || hasErrors;
}

async function handleSubmitOrder() {
  clearAlert();
  
  if (uploadedFiles.length === 0) {
    setAlert('Please upload at least one file before submitting.');
    return;
  }

  const button = document.getElementById('submitOrderBtn');
  button.disabled = true;
  button.textContent = 'Submitting…';

  try {
    for (const file of uploadedFiles) {
      const formData = new FormData();
      formData.append('file', file.fileObj);
      formData.append('print_mode', file.printMode);
      formData.append('copies', file.copies);
      formData.append('range_type', file.rangeMode);
      formData.append('page_range', file.pageRange);
      formData.append('paper_size', file.paperSize);

      const response = await fetch(`${CONFIG.API_BASE}/orders`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Failed to submit file: ${file.name}`);
      }
    }

    // Success - clear all
    uploadedFiles = [];
    activeFileId = null;
    
    document.getElementById('fileInput').value = '';
    renderFileList();
    renderConfigPanel();
    renderSummary();

    showToast('Orders submitted successfully!');
  } catch (err) {
    setAlert(err.message || 'Network error. Please check your connection and try again.');
  } finally {
    if (uploadedFiles.length > 0) {
      button.disabled = false;
    }
    button.textContent = 'Submit order';
  }
}
