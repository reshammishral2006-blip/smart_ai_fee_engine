// Dynamic host detection: Works on both local development and Render deployment
const API = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? 'http://localhost:5001' 
  : '';

const toast = (msg, type='info') => {
  const el = document.getElementById('toast') || (() => {
    const d = document.createElement('div'); 
    d.id='toast'; 
    document.body.appendChild(d); 
    return d; 
  })();
  const t = document.createElement('div'); 
  t.className='toast-msg';
  const colors = { success:'#10b981', danger:'#ef4444', warning:'#f59e0b', info:'#3b82f6' };
  t.style.borderLeft = `4px solid ${colors[type]||colors.info}`;
  t.textContent = msg; 
  el.appendChild(t);
  setTimeout(() => t.remove(), 3500);
};

const fmt = (n) => '₹' + parseFloat(n||0).toLocaleString('en-IN', { minimumFractionDigits:0, maximumFractionDigits:0 });

const api = async (path, opts={}) => {
  try {
    // Ensure path starts with /
    const cleanPath = path.startsWith('/') ? path : '/' + path;
    const r = await fetch(API + cleanPath, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    
    if (!r.ok) {
      const msg = `API Error: ${r.status} ${r.statusText}`;
      toast(msg, 'danger');
      return null;
    }
    return await r.json();
  } catch(e) {
    console.error(e);
    toast('API Error: Failed to connect to backend. Please check server connection.', 'danger');
    return null;
  }
};

const statusBadge = (s) => {
  const map = { 'Fully Paid':'success', 'Half Paid':'warning', 'Overdue':'danger', 'Pending':'warning', 'Paid':'success' };
  return `<span class="badge badge-${map[s]||'muted'}">${s}</span>`;
};

const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }) : '—';

const showModal = (id) => document.getElementById(id)?.classList.add('open');
const hideModal = (id) => document.getElementById(id)?.classList.remove('open');

const logout = (role='student') => {
  localStorage.clear();
  window.location.href = role==='admin' ? '../../index.html' : '../../index.html';
};
