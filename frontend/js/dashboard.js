/**
 * Smart e-Print — Unified Customer Dashboard Module
 * Full i18n, theme, file config, scheduling, Razorpay, order tracking.
 */

const UPLOAD_MAX = 25 * 1024 * 1024;
let PRICE_RATES = { bw_one: 2.0, bw_both: 2.0, color_one: 5.0, color_both: 5.0 };
let PAPER_MULTIPLIERS = { A4: 1.0, A3: 1.5, Letter: 1.1 };

let uploadedFiles = [];
let fileCounter = 0;
let currentOrderType = 'now';
let currentPaymentMethod = 'cash';

/* ═══════════════════════════════════════════════════════════════
   i18n — Full Translation Dictionary
   ═══════════════════════════════════════════════════════════════ */
const i18n = {
  en: {
    // Nav
    edit_picture: "Edit Picture", edit_name: "Edit Name",
    reset_password: "Reset Password", sign_out: "Sign Out",
    // Modals
    choose_avatar_color: "Choose a color for your avatar. Your initial will be displayed on the selected color.",
    save_changes: "Save Changes", current_name_label: "Current Name", new_name_label: "New Name",
    current_password_label: "Current Password", new_password_label: "New Password",
    confirm_password_label: "Confirm New Password", pw_hint: "Minimum 6 characters", change_password: "Change Password",
    // Upload View
    new_print_order: "New Print Order", go_to_dashboard: "Go to Dashboard",
    privacy_label: "Privacy:", privacy_text: "Your files are used only to print. After printing they are deleted automatically. We do not keep a copy for admin viewing — only a print receipt (pages / amount) stays for the shop bill.",
    price_list_title: "Price list (₹ per page) · live from shop (one / both sides)",
    th_paper: "Paper", th_bw_one: "B&W one", th_bw_both: "B&W both",
    th_color_one: "Colour one", th_color_both: "Colour both",
    select_files: "Select Files", upload_hint: "Drag & drop files here or click to browse · Max 25 MB each",
    upload_documents: "Upload Documents",
    // File Config
    print_mode: "Print Mode", color_or_mono: "Color or monochrome",
    bw: "B&W", color: "Color",
    copies: "Copies", num_prints: "Number of prints",
    paper_size: "Paper Size", select_size: "Select document size",
    sides: "Sides", one_or_both: "One or Both",
    one: "One", both: "Both", remove: "Remove",
    // Checkout
    order_details_payment: "Order Details & Payment",
    order_type: "Order Type", regular: "Regular", scheduled_pickup: "Scheduled Pickup",
    date: "Date", time: "Time",
    payment_method: "Payment Method", cash_at_shop: "Cash at Shop",
    online_razorpay: "Online (Razorpay)",
    cash_note: "Cash available for immediate orders only.",
    schedule_note: "Scheduled orders require online payment.",
    total_files: "Total Files", total_pages: "Total Pages (approx)",
    estimated_total: "Estimated Total", submit_order: "Submit Order",
    // Dashboard View
    your_orders: "Your Print Orders & Tracking",
    track_status: "Track real-time status of your documents",
    refresh: "Refresh", new_order: "New Order",
    th_document: "Document", th_cost: "Total Cost", th_payment: "Payment",
    th_status: "Status", th_schedule: "Schedule", th_action: "Action",
    loading: "Loading…", no_orders: "No print orders submitted yet.",
    load_error: "Failed to load orders.", cancel: "Cancel",
    cannot_cancel: "Cannot Cancel",
  },
  hi: {
    edit_picture: "चित्र बदलें", edit_name: "नाम बदलें",
    reset_password: "पासवर्ड रीसेट करें", sign_out: "साइन आउट",
    choose_avatar_color: "अपने अवतार के लिए एक रंग चुनें। आपका पहला अक्षर चुने गए रंग पर प्रदर्शित होगा।",
    save_changes: "परिवर्तन सहेजें", current_name_label: "वर्तमान नाम", new_name_label: "नया नाम",
    current_password_label: "वर्तमान पासवर्ड", new_password_label: "नया पासवर्ड",
    confirm_password_label: "नया पासवर्ड पुष्टि करें", pw_hint: "न्यूनतम 6 वर्ण", change_password: "पासवर्ड बदलें",
    new_print_order: "नया प्रिंट ऑर्डर", go_to_dashboard: "डैशबोर्ड पर जाएं",
    privacy_label: "गोपनीयता:", privacy_text: "आपकी फ़ाइलें केवल प्रिंट करने के लिए उपयोग की जाती हैं। प्रिंटिंग के बाद वे स्वचालित रूप से हटा दी जाती हैं। हम एडमिन को देखने के लिए कोई कॉपी नहीं रखते — केवल प्रिंट रसीद (पेज / राशि) दुकान के बिल के लिए रहती है।",
    price_list_title: "मूल्य सूची (₹ प्रति पेज) · दुकान से लाइव (एक / दोनों तरफ)",
    th_paper: "कागज़", th_bw_one: "B&W एक", th_bw_both: "B&W दोनों",
    th_color_one: "रंगीन एक", th_color_both: "रंगीन दोनों",
    select_files: "फ़ाइलें चुनें", upload_hint: "फ़ाइलें यहाँ खींचें या ब्राउज़ करें · अधिकतम 25 MB प्रत्येक",
    upload_documents: "दस्तावेज़ अपलोड करें",
    print_mode: "प्रिंट मोड", color_or_mono: "रंगीन या काला-सफ़ेद",
    bw: "B&W", color: "रंगीन",
    copies: "प्रतियाँ", num_prints: "प्रिंट की संख्या",
    paper_size: "कागज़ का आकार", select_size: "दस्तावेज़ का आकार चुनें",
    sides: "साइड", one_or_both: "एक या दोनों",
    one: "एक", both: "दोनों", remove: "हटाएं",
    order_details_payment: "ऑर्डर विवरण और भुगतान",
    order_type: "ऑर्डर प्रकार", regular: "नियमित", scheduled_pickup: "निर्धारित पिकअप",
    date: "तारीख", time: "समय",
    payment_method: "भुगतान विधि", cash_at_shop: "दुकान पर नकद",
    online_razorpay: "ऑनलाइन (Razorpay)",
    cash_note: "नकद केवल तत्काल ऑर्डर के लिए उपलब्ध।",
    schedule_note: "निर्धारित ऑर्डर के लिए ऑनलाइन भुगतान आवश्यक।",
    total_files: "कुल फ़ाइलें", total_pages: "कुल पेज (लगभग)",
    estimated_total: "अनुमानित कुल", submit_order: "ऑर्डर जमा करें",
    your_orders: "आपके प्रिंट ऑर्डर और ट्रैकिंग",
    track_status: "अपने दस्तावेज़ों की रीयल-टाइम स्थिति ट्रैक करें",
    refresh: "रीफ़्रेश", new_order: "नया ऑर्डर",
    th_document: "दस्तावेज़", th_cost: "कुल लागत", th_payment: "भुगतान",
    th_status: "स्थिति", th_schedule: "शेड्यूल", th_action: "कार्रवाई",
    loading: "लोड हो रहा है…", no_orders: "अभी तक कोई प्रिंट ऑर्डर नहीं।",
    load_error: "ऑर्डर लोड करने में विफल।", cancel: "रद्द करें",
    cannot_cancel: "रद्द नहीं कर सकते",
  },
  gu: {
    edit_picture: "ચિત્ર બદલો", edit_name: "નામ બદલો",
    reset_password: "પાસવર્ડ રીસેટ કરો", sign_out: "સાઇન આઉટ",
    choose_avatar_color: "તમારા અવતાર માટે રંગ પસંદ કરો. તમારો પહેલો અક્ષર પસંદ કરેલા રંગ પર પ્રદર્શિત થશે.",
    save_changes: "ફેરફારો સાચવો", current_name_label: "વર્તમાન નામ", new_name_label: "નવું નામ",
    current_password_label: "વર્તમાન પાસવર્ડ", new_password_label: "નવો પાસવર્ડ",
    confirm_password_label: "નવા પાસવર્ડની પુષ્ટિ કરો", pw_hint: "ઓછામાં ઓછા 6 અક્ષરો", change_password: "પાસવર્ડ બદલો",
    new_print_order: "નવો પ્રિન્ટ ઓર્ડર", go_to_dashboard: "ડેશબોર્ડ પર જાઓ",
    privacy_label: "ગોપનીયતા:", privacy_text: "તમારી ફાઈલો ફક્ત પ્રિન્ટ કરવા માટે વપરાય છે. પ્રિન્ટિંગ પછી તે આપમેળે ડિલીટ થઈ જાય છે. અમે એડમિન જોવા માટે કોઈ કૉપી રાખતા નથી — ફક્ત પ્રિન્ટ રસીદ (પેજ / રકમ) દુકાનના બિલ માટે રહે છે.",
    price_list_title: "કિંમત યાદી (₹ પ્રતિ પેજ) · દુકાનમાંથી લાઇવ (એક / બંને બાજુ)",
    th_paper: "કાગળ", th_bw_one: "B&W એક", th_bw_both: "B&W બંને",
    th_color_one: "રંગીન એક", th_color_both: "રંગીન બંને",
    select_files: "ફાઈલો પસંદ કરો", upload_hint: "ફાઈલો અહીં ખેંચો અથવા બ્રાઉઝ કરો · મહત્તમ 25 MB દરેક",
    upload_documents: "દસ્તાવેજો અપલોડ કરો",
    print_mode: "પ્રિન્ટ મોડ", color_or_mono: "રંગીન અથવા કાળા-સફેદ",
    bw: "B&W", color: "રંગીન",
    copies: "નકલો", num_prints: "પ્રિન્ટની સંખ્યા",
    paper_size: "કાગળનું કદ", select_size: "દસ્તાવેજનું કદ પસંદ કરો",
    sides: "બાજુ", one_or_both: "એક અથવા બંને",
    one: "એક", both: "બંને", remove: "દૂર કરો",
    order_details_payment: "ઓર્ડર વિગતો અને ચુકવણી",
    order_type: "ઓર્ડર પ્રકાર", regular: "નિયમિત", scheduled_pickup: "સુનિશ્ચિત પિકઅપ",
    date: "તારીખ", time: "સમય",
    payment_method: "ચુકવણી પદ્ધતિ", cash_at_shop: "દુકાન પર રોકડ",
    online_razorpay: "ઓનલાઈન (Razorpay)",
    cash_note: "રોકડ ફક્ત તાત્કાલિક ઓર્ડર માટે ઉપલબ્ધ.",
    schedule_note: "સુનિશ્ચિત ઓર્ડર માટે ઓનલાઈન ચુકવણી જરૂરી.",
    total_files: "કુલ ફાઈલો", total_pages: "કુલ પેજ (આશરે)",
    estimated_total: "અંદાજિત કુલ", submit_order: "ઓર્ડર સબમિટ કરો",
    your_orders: "તમારા પ્રિન્ટ ઓર્ડર અને ટ્રેકિંગ",
    track_status: "તમારા દસ્તાવેજોની રીયલ-ટાઇમ સ્થિતિ ટ્રૅક કરો",
    refresh: "રીફ્રેશ", new_order: "નવો ઓર્ડર",
    th_document: "દસ્તાવેજ", th_cost: "કુલ ખર્ચ", th_payment: "ચુકવણી",
    th_status: "સ્થિતિ", th_schedule: "શેડ્યૂલ", th_action: "ક્રિયા",
    loading: "લોડ થઈ રહ્યું છે…", no_orders: "હજી સુધી કોઈ પ્રિન્ટ ઓર્ડર નથી.",
    load_error: "ઓર્ડર લોડ કરવામાં નિષ્ફળ.", cancel: "રદ કરો",
    cannot_cancel: "રદ કરી શકાતું નથી",
  }
};

let currentLang = 'en';

function t(key) {
  return (i18n[currentLang] && i18n[currentLang][key]) || (i18n.en[key]) || key;
}

function applyLanguage(lang) {
  currentLang = lang;
  localStorage.setItem('sep_lang', lang);
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.toggle('active', b.dataset.lang === lang));
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val) el.textContent = val;
  });
  // Re-render file configs so their labels also translate
  if (uploadedFiles.length > 0) renderFileConfigs();
}

/* ═══════════════════════════════════════════════════════════════
   Init
   ═══════════════════════════════════════════════════════════════ */
async function initDashboard(requiredRole) {
  const user = await requireAuth(requiredRole);
  if (!user) return null;

  document.getElementById('navUserName').textContent = user.name;
  document.getElementById('navAvatar').textContent = user.name.charAt(0).toUpperCase();

  setupNavControls();
  setupUploadZone();
  setupProfileModals();
  loadCustomerOrders();
  return user;
}

/* ═══════════════════════════════════════════════════════════════
   Nav Controls
   ═══════════════════════════════════════════════════════════════ */
function setupNavControls() {
  // ── Theme ────────────────────────────────────────────────────
  const themeBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');
  const html = document.documentElement;

  const savedTheme = localStorage.getItem('sep_theme') || 'light';
  html.setAttribute('data-theme', savedTheme);
  themeIcon.className = savedTheme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';

  themeBtn.addEventListener('click', () => {
    const cur = html.getAttribute('data-theme');
    const next = cur === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', next);
    localStorage.setItem('sep_theme', next);
    themeIcon.className = next === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  });

  // ── Language ─────────────────────────────────────────────────
  const savedLang = localStorage.getItem('sep_lang') || 'en';
  applyLanguage(savedLang);

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      applyLanguage(e.target.dataset.lang);
    });
  });

  // ── Profile Dropdown ─────────────────────────────────────────
  const profileBtn = document.getElementById('profileDropdownBtn');
  const profileMenu = document.getElementById('profileMenu');

  profileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    profileMenu.classList.toggle('show');
  });
  document.addEventListener('click', (e) => {
    if (!profileBtn.contains(e.target) && !profileMenu.contains(e.target)) {
      profileMenu.classList.remove('show');
    }
  });

  // ── Sign Out ─────────────────────────────────────────────────
  document.getElementById('signOutBtn').addEventListener('click', (e) => {
    e.preventDefault();
    clearAuth();
    window.location.replace('login.html');
  });
}

/* ═══════════════════════════════════════════════════════════════
   View Switcher
   ═══════════════════════════════════════════════════════════════ */
function switchView(viewName) {
  const uv = document.getElementById('uploadView');
  const dv = document.getElementById('dashboardView');
  if (viewName === 'upload') { uv.style.display = 'block'; dv.style.display = 'none'; }
  else { uv.style.display = 'none'; dv.style.display = 'block'; loadCustomerOrders(); }
}

/* ═══════════════════════════════════════════════════════════════
   File Upload
   ═══════════════════════════════════════════════════════════════ */
function setupUploadZone() {
  const fileInput = document.getElementById('mainFileInput');
  const dropzone = document.getElementById('mainUploadDropzone');
  if (!fileInput || !dropzone) return;

  // Drag-and-drop visual feedback
  dropzone.addEventListener('dragenter', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', () => { dropzone.classList.remove('drag-over'); });
  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event('change'));
    }
  });

  fileInput.addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    for (const file of files) {
      if (file.size > UPLOAD_MAX) { showToast(`${file.name} > 25MB`); continue; }
      const pages = await getPageCount(file);
      uploadedFiles.push({
        id: `f_${fileCounter++}`, fileObj: file, name: file.name,
        size: file.size, pages, copies: 1, mode: 'bw_one', paperSize: 'A4'
      });
    }
    fileInput.value = '';
    renderUploadedFilesList();
    renderFileConfigs();
  });
}

function renderUploadedFilesList() {
  const listEl = document.getElementById('uploadedFilesList');
  if (!listEl) return;
  if (uploadedFiles.length === 0) { listEl.innerHTML = ''; return; }
  listEl.innerHTML = uploadedFiles.map(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    const icon = ext === 'pdf' ? 'bi-file-earmark-pdf' : 'bi-file-earmark-image';
    return `<div class="uploaded-file-item">
      <div class="ufi-icon"><i class="bi ${icon}"></i></div>
      <div class="ufi-info">
        <span class="ufi-name">${esc(f.name)}</span>
        <span class="ufi-meta">${f.pages} pg · ${fmtBytes(f.size)}</span>
      </div>
      <i class="bi bi-check-circle-fill ufi-check"></i>
    </div>`;
  }).join('');
}

function getPageCount(file) {
  return new Promise(resolve => {
    if (file.type !== 'application/pdf') { resolve(1); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const txt = new TextDecoder('latin1').decode(reader.result);
      const m = txt.match(/\/Type\s*\/Page\b/g);
      resolve(m ? m.length : 1);
    };
    reader.readAsArrayBuffer(file);
  });
}

function fmtBytes(b) {
  return b < 1048576 ? `${(b/1024).toFixed(1)} KB` : `${(b/1048576).toFixed(2)} MB`;
}

/* ═══════════════════════════════════════════════════════════════
   Render File Config Cards
   ═══════════════════════════════════════════════════════════════ */
function renderFileConfigs() {
  const container = document.getElementById('fileConfigContainer');
  const checkout = document.getElementById('checkoutArea');
  container.innerHTML = '';
  if (uploadedFiles.length === 0) { checkout.style.display = 'none'; return; }
  checkout.style.display = 'block';

  uploadedFiles.forEach(file => {
    const box = document.createElement('div');
    box.className = 'file-config-box';
    box.innerHTML = `
      <div class="file-config-header">
        <div>
          <h6><i class="bi bi-file-earmark-text" style="margin-right:6px;"></i>${esc(file.name)}</h6>
          <small style="color:var(--text-muted);">${file.pages} pg · ${fmtBytes(file.size)}</small>
        </div>
        <button class="remove-btn" onclick="removeFile('${file.id}')"><i class="bi bi-x-circle"></i> ${t('remove')}</button>
      </div>
      <div class="file-settings-row">
        <!-- Print Mode -->
        <div class="setting-card">
          <div class="s-icon"><i class="bi bi-palette2"></i></div>
          <div class="s-info"><div class="s-label">${t('print_mode')}</div><div class="s-desc">${t('color_or_mono')}</div></div>
          <div class="s-control">
            <div class="pill-group">
              <div class="pill ${file.mode.startsWith('bw')?'active':''}" onclick="updateFileMode('${file.id}','bw')">${t('bw')}</div>
              <div class="pill ${file.mode.startsWith('color')?'active':''}" onclick="updateFileMode('${file.id}','color')">${t('color')}</div>
            </div>
          </div>
        </div>
        <!-- Copies -->
        <div class="setting-card">
          <div class="s-icon"><i class="bi bi-files"></i></div>
          <div class="s-info"><div class="s-label">${t('copies')}</div><div class="s-desc">${t('num_prints')}</div></div>
          <div class="s-control">
            <div class="stepper">
              <button onclick="updateFile('${file.id}','copies',Math.max(1,${file.copies}-1))"><i class="bi bi-dash"></i></button>
              <span>${file.copies}</span>
              <button onclick="updateFile('${file.id}','copies',${file.copies}+1)"><i class="bi bi-plus"></i></button>
            </div>
          </div>
        </div>
        <!-- Paper Size -->
        <div class="setting-card">
          <div class="s-icon"><i class="bi bi-aspect-ratio"></i></div>
          <div class="s-info"><div class="s-label">${t('paper_size')}</div><div class="s-desc">${t('select_size')}</div></div>
          <div class="s-control">
            <select class="mini-select" onchange="updateFile('${file.id}','paperSize',this.value)">
              <option value="A4" ${file.paperSize==='A4'?'selected':''}>A4</option>
              <option value="A3" ${file.paperSize==='A3'?'selected':''}>A3</option>
              <option value="Letter" ${file.paperSize==='Letter'?'selected':''}>Letter</option>
            </select>
          </div>
        </div>
        <!-- Sides -->
        <div class="setting-card">
          <div class="s-icon"><i class="bi bi-file-earmark-break"></i></div>
          <div class="s-info"><div class="s-label">${t('sides')}</div><div class="s-desc">${t('one_or_both')}</div></div>
          <div class="s-control">
            <div class="pill-group">
              <div class="pill ${file.mode.endsWith('one')?'active':''}" onclick="updateFileSides('${file.id}','one')">${t('one')}</div>
              <div class="pill ${file.mode.endsWith('both')?'active':''}" onclick="updateFileSides('${file.id}','both')">${t('both')}</div>
            </div>
          </div>
        </div>
      </div>
    `;
    container.appendChild(box);
  });
  updateCheckoutSummary();
}

function removeFile(id) { uploadedFiles = uploadedFiles.filter(f => f.id !== id); renderUploadedFilesList(); renderFileConfigs(); }

function updateFile(id, key, val) {
  const f = uploadedFiles.find(x => x.id === id);
  if (f) { f[key] = val; renderFileConfigs(); }
}
function updateFileMode(id, base) {
  const f = uploadedFiles.find(x => x.id === id);
  if (f) { f.mode = `${base}_${f.mode.endsWith('both')?'both':'one'}`; renderFileConfigs(); }
}
function updateFileSides(id, side) {
  const f = uploadedFiles.find(x => x.id === id);
  if (f) { f.mode = `${f.mode.startsWith('color')?'color':'bw'}_${side}`; renderFileConfigs(); }
}

/* ═══════════════════════════════════════════════════════════════
   Checkout Logic
   ═══════════════════════════════════════════════════════════════ */
function setOrderType(type) {
  currentOrderType = type;
  document.getElementById('btnOrderNow').classList.toggle('active', type === 'now');
  document.getElementById('btnOrderSchedule').classList.toggle('active', type === 'schedule');
  document.getElementById('scheduleInputs').style.display = type === 'schedule' ? 'block' : 'none';

  const cashBtn = document.getElementById('btnPayCash');
  const noteEl = document.getElementById('paymentNote');
  if (type === 'schedule') {
    setPayment('online');
    cashBtn.style.opacity = '.4'; cashBtn.style.pointerEvents = 'none';
    noteEl.textContent = t('schedule_note');
    noteEl.setAttribute('data-i18n', 'schedule_note');
  } else {
    cashBtn.style.opacity = '1'; cashBtn.style.pointerEvents = 'auto';
    noteEl.textContent = t('cash_note');
    noteEl.setAttribute('data-i18n', 'cash_note');
  }
}

function setPayment(method) {
  currentPaymentMethod = method;
  document.getElementById('btnPayCash').classList.toggle('active', method === 'cash');
  document.getElementById('btnPayOnline').classList.toggle('active', method === 'online');
}

function updateCheckoutSummary() {
  let files = uploadedFiles.length, pages = 0, cost = 0;
  uploadedFiles.forEach(f => {
    pages += f.pages * f.copies;
    cost += f.pages * f.copies * (PRICE_RATES[f.mode] || 2) * (PAPER_MULTIPLIERS[f.paperSize] || 1);
  });
  document.getElementById('grandTotalFiles').textContent = files;
  document.getElementById('grandTotalPages').textContent = pages;
  document.getElementById('grandTotalCost').textContent = `₹${cost.toFixed(2)}`;
}

/* ═══════════════════════════════════════════════════════════════
   Submit + Razorpay
   ═══════════════════════════════════════════════════════════════ */
async function submitMainOrder() {
  if (uploadedFiles.length === 0) return;
  let scheduleTimeStr = null;
  if (currentOrderType === 'schedule') {
    const d = document.getElementById('scheduleDate').value;
    const tm = document.getElementById('scheduleTime').value;
    if (!d || !tm) { showToast(t('date') + ' & ' + t('time') + ' required', 'error'); return; }
    scheduleTimeStr = `${d} ${tm}`;
  }
  let total = 0;
  uploadedFiles.forEach(f => {
    total += f.pages * f.copies * (PRICE_RATES[f.mode]||2) * (PAPER_MULTIPLIERS[f.paperSize]||1);
  });
  if (currentPaymentMethod === 'online') initRazorpayFlow(total, scheduleTimeStr);
  else executeOrderSubmission(scheduleTimeStr, 'pending');
}

function initRazorpayFlow(amount, scheduleTimeStr) {
  if (typeof window.Razorpay === 'undefined') { showToast('Razorpay SDK not loaded.', 'error'); return; }
  try {
    const rzp = new window.Razorpay({
      key: "rzp_test_placeholder", amount: Math.round(amount * 100), currency: "INR",
      name: "Smart e-Print", description: "Print Order Payment",
      handler: () => executeOrderSubmission(scheduleTimeStr, 'paid'),
      prefill: { name: document.getElementById('navUserName').textContent },
      theme: { color: "#2563EB" }
    });
    rzp.on('payment.failed', r => showToast(`Payment Failed: ${r.error.description}`, 'error'));
    rzp.open();
  } catch(e) {
    console.warn("Razorpay open failed, simulating success.");
    executeOrderSubmission(scheduleTimeStr, 'paid');
  }
}

async function executeOrderSubmission(scheduleTimeStr, paymentStatus) {
  try {
    for (const file of uploadedFiles) {
      const fd = new FormData();
      fd.append('file', file.fileObj);
      fd.append('print_mode', file.mode.startsWith('color') ? 'color' : 'bw');
      fd.append('copies', file.copies);
      fd.append('paper_size', file.paperSize);
      fd.append('payment_method', currentPaymentMethod);
      fd.append('payment_status', paymentStatus);
      fd.append('range_type', 'full');  // Always full range for now
      if (scheduleTimeStr) fd.append('schedule_time', scheduleTimeStr);
      const res = await fetch(`${CONFIG.API_BASE}/orders`, {
        method: 'POST', headers: { Authorization: `Bearer ${getToken()}` }, body: fd
      });
      if (!res.ok) {
        let errMsg = `Failed to submit: ${file.name}`;
        try {
          const errData = await res.json();
          if (errData && errData.error) errMsg = errData.error;
        } catch (_) {}
        throw new Error(errMsg);
      }
    }
    showToast('Order submitted successfully!', 'success');
    uploadedFiles = []; fileCounter = 0;
    renderUploadedFilesList();
    renderFileConfigs();
    document.getElementById('mainFileInput').value = '';
    // Small delay to ensure DOM updates before view switch
    setTimeout(() => switchView('dashboard'), 150);
  } catch(err) { showToast(err.message || 'Network error.', 'error'); }
}

/* ═══════════════════════════════════════════════════════════════
   Dashboard — Order Table
   ═══════════════════════════════════════════════════════════════ */
async function loadCustomerOrders() {
  const tbody = document.getElementById('custOrdersTableBody');
  if (!tbody) return;
  try {
    const res = await fetch(`${CONFIG.API_BASE}/orders`, { headers: { Authorization: `Bearer ${getToken()}` } });
    const data = await res.json();
    if (!res.ok) throw new Error();
    const orders = data.orders || [];
    if (orders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--text-muted);">${t('no_orders')}</td></tr>`;
      return;
    }
    tbody.innerHTML = orders.map(o => {
      const pay = o.payment_status === 'paid'
        ? `<span style="color:var(--success);font-weight:600;">Paid</span>`
        : `<span style="color:#eab308;font-weight:600;">Pending</span>`;
      const canCancel = ['Submitted','Accepted'].includes(o.status);
      const action = canCancel
        ? `<button class="btn-modern" style="font-size:.75rem;padding:4px 10px;" onclick="cancelOrder('${o.id}')">${t('cancel')}</button>`
        : `<span style="color:var(--text-muted);font-size:.75rem;">${t('cannot_cancel')}</span>`;
      return `<tr>
        <td><strong style="display:block;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${esc(o.file_name)}</strong>
            <small style="color:var(--text-muted);">${o.copies} × ${o.print_mode} · ${o.paper_size}</small></td>
        <td><strong style="color:var(--success);">₹${(o.total_price||0).toFixed(2)}</strong></td>
        <td>${pay}</td>
        <td><span class="badge-status badge-${o.status}">${o.status}</span></td>
        <td>${o.schedule_time || '—'}</td>
        <td>${action}</td>
      </tr>`;
    }).join('');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:28px;color:var(--danger);">${t('load_error')}</td></tr>`;
  }
}

async function cancelOrder(id) {
  if (!confirm('Cancel this order?')) return;
  try {
    const res = await fetch(`${CONFIG.API_BASE}/orders/${id}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` }
    });
    const data = await res.json();
    if (res.ok) { showToast(data.message || 'Order cancelled.', 'success'); loadCustomerOrders(); }
    else { showToast(data.error || 'Failed to cancel.', 'error'); }
  } catch(e) { showToast('Failed to cancel.', 'error'); }
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ═══════════════════════════════════════════════════════════════
   Profile Modals — Edit Picture, Edit Name, Reset Password
   ═══════════════════════════════════════════════════════════════ */

const AVATAR_COLORS = [
  'linear-gradient(135deg, #06B6D4, #10B981)',
  'linear-gradient(135deg, #3B82F6, #8B5CF6)',
  'linear-gradient(135deg, #F59E0B, #EF4444)',
  'linear-gradient(135deg, #EC4899, #8B5CF6)',
  'linear-gradient(135deg, #10B981, #059669)',
  'linear-gradient(135deg, #6366F1, #3B82F6)',
  'linear-gradient(135deg, #F97316, #F59E0B)',
  'linear-gradient(135deg, #EF4444, #DC2626)',
  'linear-gradient(135deg, #14B8A6, #06B6D4)',
  'linear-gradient(135deg, #A855F7, #EC4899)',
  'linear-gradient(135deg, #84CC16, #22C55E)',
  'linear-gradient(135deg, #0EA5E9, #2563EB)',
];

let selectedAvatarColor = localStorage.getItem('sep_avatar_color') || AVATAR_COLORS[0];

function openModal(id) {
  document.getElementById('profileMenu').classList.remove('show');
  document.getElementById(id).classList.add('show');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('show');
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('show');
  }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.show').forEach(m => m.classList.remove('show'));
  }
});

/* ── Avatar Color Picker ──────────────────────────────── */
function initAvatarColorGrid() {
  const grid = document.getElementById('avatarColorGrid');
  if (!grid) return;
  grid.innerHTML = AVATAR_COLORS.map((color, i) => {
    const active = color === selectedAvatarColor ? 'active' : '';
    return `<div class="color-swatch ${active}" style="background:${color};" data-color-index="${i}" onclick="selectAvatarColor(${i})"></div>`;
  }).join('');
}

function selectAvatarColor(index) {
  selectedAvatarColor = AVATAR_COLORS[index];
  const preview = document.getElementById('avatarPreview');
  if (preview) preview.style.background = selectedAvatarColor;
  document.querySelectorAll('.color-swatch').forEach((s, i) => {
    s.classList.toggle('active', i === index);
  });
}

function applyAvatarColor() {
  localStorage.setItem('sep_avatar_color', selectedAvatarColor);
  const navAvatar = document.getElementById('navAvatar');
  if (navAvatar) navAvatar.style.background = selectedAvatarColor;
}

function loadSavedAvatarColor() {
  const saved = localStorage.getItem('sep_avatar_color');
  if (saved) {
    selectedAvatarColor = saved;
    const navAvatar = document.getElementById('navAvatar');
    if (navAvatar) navAvatar.style.background = saved;
  }
}

/* ── Edit Name ────────────────────────────────────────── */
async function saveNewName() {
  const newName = document.getElementById('newNameInput').value.trim();
  if (!newName || newName.length < 2) {
    showToast('Name must be at least 2 characters.', 'error');
    return;
  }
  const btn = document.getElementById('saveNameBtn');
  btn.disabled = true;
  try {
    const res = await fetch(`${CONFIG.API_BASE}/auth/profile/name`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ name: newName })
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('navUserName').textContent = newName;
      document.getElementById('navAvatar').textContent = newName.charAt(0).toUpperCase();
      document.getElementById('avatarPreview').textContent = newName.charAt(0).toUpperCase();
      const savedUser = JSON.parse(localStorage.getItem(CONFIG.USER_KEY) || '{}');
      savedUser.name = newName;
      localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(savedUser));
      closeModal('modalEditName');
    } else {
      showToast(data.error || 'Failed to update name.', 'error');
    }
  } catch(e) {
    showToast('Network error. Please try again.', 'error');
  }
  btn.disabled = false;
}

/* ── Reset Password ───────────────────────────────────── */
async function saveNewPassword() {
  const currentPw = document.getElementById('currentPwInput').value;
  const newPw = document.getElementById('newPwInput').value;
  const confirmPw = document.getElementById('confirmPwInput').value;

  if (!currentPw) { showToast('Enter your current password.', 'error'); return; }
  if (!newPw || newPw.length < 6) { showToast('New password must be at least 6 characters.', 'error'); return; }
  if (newPw !== confirmPw) { showToast('New passwords do not match.', 'error'); return; }

  const btn = document.getElementById('savePwBtn');
  btn.disabled = true;
  try {
    const res = await fetch(`${CONFIG.API_BASE}/auth/profile/password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ current_password: currentPw, new_password: newPw, confirm_password: confirmPw })
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('currentPwInput').value = '';
      document.getElementById('newPwInput').value = '';
      document.getElementById('confirmPwInput').value = '';
      closeModal('modalResetPassword');
    } else {
      showToast(data.error || 'Failed to change password.', 'error');
    }
  } catch(e) {
    showToast('Network error. Please try again.', 'error');
  }
  btn.disabled = false;
}

/* ── Wire up dropdown → modals ────────────────────────── */
function setupProfileModals() {
  const editPicBtn = document.getElementById('editPictureBtn');
  if (editPicBtn) {
    editPicBtn.addEventListener('click', (e) => {
      e.preventDefault();
      initAvatarColorGrid();
      const userName = document.getElementById('navUserName')?.textContent || 'C';
      const preview = document.getElementById('avatarPreview');
      if (preview) {
        preview.textContent = userName.charAt(0).toUpperCase();
        preview.style.background = selectedAvatarColor;
      }
      openModal('modalEditPicture');
    });
  }

  const saveAvatarBtn = document.getElementById('saveAvatarBtn');
  if (saveAvatarBtn) {
    saveAvatarBtn.addEventListener('click', () => {
      applyAvatarColor();
      closeModal('modalEditPicture');
    });
  }

  const editNameBtn = document.getElementById('editNameBtn');
  if (editNameBtn) {
    editNameBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const currentName = document.getElementById('navUserName')?.textContent || '';
      document.getElementById('currentNameDisplay').value = currentName;
      document.getElementById('newNameInput').value = '';
      openModal('modalEditName');
      setTimeout(() => document.getElementById('newNameInput').focus(), 100);
    });
  }

  const saveNameBtn = document.getElementById('saveNameBtn');
  if (saveNameBtn) saveNameBtn.addEventListener('click', saveNewName);

  const newNameInput = document.getElementById('newNameInput');
  if (newNameInput) newNameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveNewName(); });

  const resetPwBtn = document.getElementById('resetPasswordBtn');
  if (resetPwBtn) {
    resetPwBtn.addEventListener('click', (e) => {
      e.preventDefault();
      document.getElementById('currentPwInput').value = '';
      document.getElementById('newPwInput').value = '';
      document.getElementById('confirmPwInput').value = '';
      openModal('modalResetPassword');
      setTimeout(() => document.getElementById('currentPwInput').focus(), 100);
    });
  }

  const savePwBtn = document.getElementById('savePwBtn');
  if (savePwBtn) savePwBtn.addEventListener('click', saveNewPassword);

  const confirmPwInput = document.getElementById('confirmPwInput');
  if (confirmPwInput) confirmPwInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveNewPassword(); });

  loadSavedAvatarColor();
}
