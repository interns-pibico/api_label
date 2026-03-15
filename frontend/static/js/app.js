/* =============================================================
   api_label — app.js v1
   Core frontend logic: auth, fetch wrapper, navigation, utilities
   ============================================================= */

'use strict';

/* ── Constants ───────────────────────────────────────────────── */
const TOKEN_KEY = 'label_token';
const USER_KEY  = 'label_user';
// Root path injected from template via global var
const ROOT = window.LABEL_ROOT || '';

/* ── Token helpers ───────────────────────────────────────────── */
const Auth = {
  getToken()  { return localStorage.getItem(TOKEN_KEY); },
  setToken(t) { localStorage.setItem(TOKEN_KEY, t); },
  removeToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  getUser()   {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  },
  setUser(u)  { localStorage.setItem(USER_KEY, JSON.stringify(u)); },
  isLoggedIn() { return !!Auth.getToken(); },
  isAdmin()   { return Auth.getUser()?.is_admin === true; },
  requireAuth() {
    if (!Auth.isLoggedIn()) {
      window.location.href = ROOT + '/login';
      return false;
    }
    return true;
  },
  requireAdmin() {
    if (!Auth.isLoggedIn()) { window.location.href = ROOT + '/login'; return false; }
    if (!Auth.isAdmin())    { window.location.href = ROOT + '/dashboard'; return false; }
    return true;
  },
};

/* ── Fetch wrapper ───────────────────────────────────────────── */
async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(ROOT + path, {
    ...options,
    headers,
  });

  // 401 → redirect to login (unless caller opts out, e.g. public pages)
  if (res.status === 401) {
    Auth.removeToken();
    if (!options.skipRedirect) {
      window.location.href = ROOT + '/login';
    }
    return null;
  }

  // Parse JSON if content-type matches
  const ct = res.headers.get('content-type') || '';
  let data = null;
  if (ct.includes('application/json')) {
    data = await res.json();
  } else if (ct.includes('text/')) {
    data = await res.text();
  } else {
    data = await res.blob();
  }

  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `Error ${res.status}`;
    throw new ApiError(msg, res.status, data);
  }
  return data;
}

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data   = data;
  }
}

/* Convenience wrappers */
const api = {
  get:    (path, opts = {})       => apiFetch(path, { method: 'GET', ...opts }),
  post:   (path, body, opts = {}) => apiFetch(path, { method: 'POST',  body: JSON.stringify(body), ...opts }),
  put:    (path, body, opts = {}) => apiFetch(path, { method: 'PUT',   body: JSON.stringify(body), ...opts }),
  patch:  (path, body, opts = {}) => apiFetch(path, { method: 'PATCH', body: JSON.stringify(body), ...opts }),
  del:    (path, opts = {})       => apiFetch(path, { method: 'DELETE', ...opts }),
  postForm: (path, formData, opts = {}) => {
    const token = Auth.getToken();
    return fetch(ROOT + path, {
      method: 'POST',
      headers: { ...(token ? { 'Authorization': `Bearer ${token}` } : {}), ...(opts.headers || {}) },
      body: formData,
    }).then(async res => {
      if (res.status === 401) { Auth.removeToken(); window.location.href = ROOT + '/login'; return null; }
      const ct = res.headers.get('content-type') || '';
      const data = ct.includes('application/json') ? await res.json() : await res.text();
      if (!res.ok) { throw new ApiError((data && (data.detail || data.message)) || `Error ${res.status}`, res.status, data); }
      return data;
    });
  },
};

/* ── Toast notifications ─────────────────────────────────────── */
const Toast = {
  show(message, type = 'info', duration = 4000) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = {
      info:    '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
      success: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error:   '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      warning: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    };
    toast.innerHTML = `${icons[type] || icons.info}<span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
  },
  success: (m) => Toast.show(m, 'success'),
  error:   (m) => Toast.show(m, 'error'),
  warning: (m) => Toast.show(m, 'warning'),
  info:    (m) => Toast.show(m, 'info'),
};

/* ── Navigation helpers ──────────────────────────────────────── */
function setActiveNav(page) {
  document.querySelectorAll('[data-page]').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
}

function initDrawer() {
  const overlay = document.getElementById('drawer-overlay');
  const drawer  = document.getElementById('drawer');
  const btnOpen = document.getElementById('btn-open-drawer');
  const btnClose= document.getElementById('btn-close-drawer');

  if (!overlay || !drawer) return;

  function open() {
    overlay.classList.add('open');
    drawer.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    overlay.classList.remove('open');
    drawer.classList.remove('open');
    document.body.style.overflow = '';
  }
  btnOpen?.addEventListener('click', open);
  btnClose?.addEventListener('click', close);
  overlay.addEventListener('click', close);
}

/* ── User info population ────────────────────────────────────── */
function populateUserInfo() {
  const user = Auth.getUser();
  if (!user) return;

  // Sidebar username / role
  document.querySelectorAll('.js-username').forEach(el => {
    el.textContent = user.full_name || user.username || '';
  });
  document.querySelectorAll('.js-userrole').forEach(el => {
    el.textContent = user.is_admin ? 'Administrador' : 'Usuario';
  });
  document.querySelectorAll('.js-avatar').forEach(el => {
    el.textContent = (user.full_name || user.username || 'U').charAt(0).toUpperCase();
  });

  // Show admin nav items
  if (user.is_admin) {
    document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
  }
}

/* ── Logout ──────────────────────────────────────────────────── */
async function logout() {
  try {
    await api.post('/api/v1/auth/logout', {});
  } catch {}
  Auth.removeToken();
  window.location.href = ROOT + '/login';
}

/* ── Modal helpers ───────────────────────────────────────────── */
const Modal = {
  open(id) {
    const m = document.getElementById(id);
    m?.classList.add('open');
  },
  close(id) {
    const m = document.getElementById(id);
    m?.classList.remove('open');
  },
  init() {
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => {
        const modal = btn.closest('.modal-backdrop');
        modal?.classList.remove('open');
      });
    });
    document.querySelectorAll('.modal-backdrop').forEach(bd => {
      bd.addEventListener('click', (e) => {
        if (e.target === bd) bd.classList.remove('open');
      });
    });
  },
};

/* ── Format helpers ──────────────────────────────────────────── */
function fmtDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('es-ES', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}
function fmtDatetime(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('es-ES', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}
function fmtRelative(iso) {
  if (!iso) return '-';
  const diff = Date.now() - new Date(iso).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60)   return 'Hace un momento';
  if (secs < 3600) return `Hace ${Math.floor(secs/60)} min`;
  if (secs < 86400) return `Hace ${Math.floor(secs/3600)} h`;
  return `Hace ${Math.floor(secs/86400)} días`;
}

/* ── Pagination helper ───────────────────────────────────────── */
function renderPagination(container, { page, pages }, onPage) {
  if (!container) return;
  container.innerHTML = '';
  if (pages <= 1) return;

  const add = (label, p, disabled = false, active = false) => {
    const btn = document.createElement('button');
    btn.className = 'page-btn' + (active ? ' active' : '');
    btn.innerHTML = label;
    btn.disabled = disabled;
    if (!disabled) btn.addEventListener('click', () => onPage(p));
    container.appendChild(btn);
  };

  add('&laquo;', 1, page === 1);
  add('&lsaquo;', page - 1, page === 1);

  const start = Math.max(1, page - 2);
  const end   = Math.min(pages, page + 2);
  for (let i = start; i <= end; i++) add(i, i, false, i === page);

  add('&rsaquo;', page + 1, page === pages);
  add('&raquo;', pages, page === pages);
}

/* ── Fetch /me and bootstrap ─────────────────────────────────── */
async function fetchAndStoreUser() {
  try {
    const user = await apiFetch('/api/v1/auth/me', { method: 'GET', skipRedirect: true });
    if (user) { Auth.setUser(user); return user; }
  } catch {}
  return null;
}

/* ── DOM ready bootstrap ─────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Populate user info if logged in
  if (Auth.isLoggedIn()) {
    populateUserInfo();
    // Refresh user data in background
    fetchAndStoreUser().then(u => { if (u) populateUserInfo(); });
  }

  // Init drawer (mobile)
  initDrawer();

  // Init modals
  Modal.init();

  // Logout buttons
  document.querySelectorAll('.js-logout').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      logout();
    });
  });
});

/* ── Export globals ──────────────────────────────────────────── */
window.Auth    = Auth;
window.api     = api;
window.Toast   = Toast;
window.Modal   = Modal;
window.fmtDate = fmtDate;
window.fmtDatetime = fmtDatetime;
window.fmtRelative = fmtRelative;
window.renderPagination = renderPagination;
window.fetchAndStoreUser = fetchAndStoreUser;
