/**
 * ESSENCE PREMIER — API Client
 * Shared across all HTML pages. Include this before any page-specific scripts.
 *
 * Usage:  <script src="api.js"></script>
 */

const API_BASE = "http://127.0.0.1:8000/api/v1";  // Change to your deployed URL in production

// ── Token helpers ─────────────────────────────────────────────────────────────

const Auth = {
  getToken()  { return localStorage.getItem("ep_token"); },
  getUser()   { const u = localStorage.getItem("ep_user"); return u ? JSON.parse(u) : null; },
  isLoggedIn(){ return !!this.getToken(); },

  save(data) {
    localStorage.setItem("ep_token", data.access_token);
    localStorage.setItem("ep_user", JSON.stringify({
      id: data.user_id,
      email: data.email,
      first_name: data.first_name,
      last_name: data.last_name,
      facility_name: data.facility_name,
    }));
  },

  clear() {
    localStorage.removeItem("ep_token");
    localStorage.removeItem("ep_user");
  },
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function apiFetch(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };

  if (auth) {
    const token = Auth.getToken();
    if (!token) {
      window.location.href = "login.html";
      throw new Error("Not authenticated");
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(API_BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  // Token expired
  if (res.status === 401) {
    Auth.clear();
    window.location.href = "login.html";
    throw new Error("Session expired. Please sign in again.");
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Something went wrong. Please try again.");
  }

  return data;
}

// ── Auth API ──────────────────────────────────────────────────────────────────

const AuthAPI = {
  async login(email, password) {
    const data = await apiFetch("/auth/login", { method: "POST", body: { email, password } });
    Auth.save(data);
    return data;
  },

  async signup(payload) {
    const data = await apiFetch("/auth/signup", { method: "POST", body: payload });
    Auth.save(data);
    return data;
  },

  async logout() {
    try { await apiFetch("/auth/logout", { method: "POST", auth: true }); } catch (_) {}
    Auth.clear();
    window.location.href = "index.html";
  },

  async me() {
    return apiFetch("/auth/me", { auth: true });
  },
};

// ── Products API ──────────────────────────────────────────────────────────────

const ProductsAPI = {
  async list({ page = 1, pageSize = 12, category, search, sortBy, order } = {}) {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (category) params.set("category", category);
    if (search)   params.set("search", search);
    if (sortBy)   params.set("sort_by", sortBy);
    if (order)    params.set("order", order);
    return apiFetch(`/products?${params}`);
  },

  async get(id)  { return apiFetch(`/products/${id}`); },
  async bySku(sku) { return apiFetch(`/products/sku/${sku}`); },
};

// ── Cart API ──────────────────────────────────────────────────────────────────

const CartAPI = {
  async get()                       { return apiFetch("/cart", { auth: true }); },
  async add(product_id, quantity=1) { return apiFetch("/cart/items", { method: "POST", auth: true, body: { product_id, quantity } }); },
  async update(item_id, quantity)   { return apiFetch(`/cart/items/${item_id}`, { method: "PATCH", auth: true, body: { quantity } }); },
  async remove(item_id)             { return apiFetch(`/cart/items/${item_id}`, { method: "DELETE", auth: true }); },
  async clear()                     { return apiFetch("/cart", { method: "DELETE", auth: true }); },
};

// ── Orders API ────────────────────────────────────────────────────────────────

const OrdersAPI = {
  async place(payload)    { return apiFetch("/orders", { method: "POST", auth: true, body: payload }); },
  async list(page=1)      { return apiFetch(`/orders?page=${page}`, { auth: true }); },
  async get(id)           { return apiFetch(`/orders/${id}`, { auth: true }); },
  async cancel(id)        { return apiFetch(`/orders/${id}/cancel`, { method: "PATCH", auth: true }); },
};

// ── CRM API ───────────────────────────────────────────────────────────────────

const CRMAPI = {
  async summary()                    { return apiFetch('/crm/summary', { auth: true }); },
  async listContacts(params = {})    { const q = new URLSearchParams(params); return apiFetch(`/crm/contacts?${q}`, { auth: true }); },
  async createContact(body)          { return apiFetch('/crm/contacts', { method: 'POST', auth: true, body }); },
  async getContact(id)               { return apiFetch(`/crm/contacts/${id}`, { auth: true }); },
  async updateContact(id, body)      { return apiFetch(`/crm/contacts/${id}`, { method: 'PATCH', auth: true, body }); },
  async deleteContact(id)            { return apiFetch(`/crm/contacts/${id}`, { method: 'DELETE', auth: true }); },
  async listInteractions(contactId)  { return apiFetch(`/crm/contacts/${contactId}/interactions`, { auth: true }); },
  async logInteraction(contactId, b) { return apiFetch(`/crm/contacts/${contactId}/interactions`, { method: 'POST', auth: true, body: b }); },
};

// ── Finance API ───────────────────────────────────────────────────────────────

const FinanceAPI = {
  async summary()                    { return apiFetch('/finance/summary', { auth: true }); },
  async revenue()                    { return apiFetch('/finance/revenue', { auth: true }); },
  async listInvoices(params = {})    { const q = new URLSearchParams(params); return apiFetch(`/finance/invoices?${q}`, { auth: true }); },
  async createInvoice(body)          { return apiFetch('/finance/invoices', { method: 'POST', auth: true, body }); },
  async getInvoice(id)               { return apiFetch(`/finance/invoices/${id}`, { auth: true }); },
  async payInvoice(id, body)         { return apiFetch(`/finance/invoices/${id}/pay`, { method: 'PATCH', auth: true, body }); },
};

// ── Supply Chain API ──────────────────────────────────────────────────────────

const SupplyChainAPI = {
  async summary()                    { return apiFetch('/supply-chain/summary', { auth: true }); },
  async listSuppliers(params = {})   { const q = new URLSearchParams(params); return apiFetch(`/supply-chain/suppliers?${q}`, { auth: true }); },
  async createSupplier(body)         { return apiFetch('/supply-chain/suppliers', { method: 'POST', auth: true, body }); },
  async updateSupplier(id, body)     { return apiFetch(`/supply-chain/suppliers/${id}`, { method: 'PATCH', auth: true, body }); },
  async listPOs(params = {})         { const q = new URLSearchParams(params); return apiFetch(`/supply-chain/purchase-orders?${q}`, { auth: true }); },
  async createPO(body)               { return apiFetch('/supply-chain/purchase-orders', { method: 'POST', auth: true, body }); },
  async updatePOStatus(id, status)   { return apiFetch(`/supply-chain/purchase-orders/${id}/status?status=${status}`, { method: 'PATCH', auth: true }); },
  async listPartners()               { return apiFetch('/supply-chain/partners', { auth: true }); },
  async createPartner(body)          { return apiFetch('/supply-chain/partners', { method: 'POST', auth: true, body }); },
};

// ── UI helpers ────────────────────────────────────────────────────────────────

function showToast(message, type = "success") {
  const existing = document.getElementById("ep-toast");
  if (existing) existing.remove();

  const colors = { success: "#00a896", error: "#dc2626", info: "#0057a8" };
  const toast = document.createElement("div");
  toast.id = "ep-toast";
  toast.style.cssText = `
    position:fixed; bottom:24px; right:24px; z-index:9999;
    background:${colors[type] || colors.info}; color:white;
    padding:14px 20px; border-radius:10px; font-size:14px; font-weight:600;
    font-family:'DM Sans',sans-serif; box-shadow:0 8px 24px rgba(0,0,0,0.2);
    animation:slideIn .3s ease; max-width:340px; line-height:1.5;
  `;
  toast.textContent = message;

  const style = document.createElement("style");
  style.textContent = `@keyframes slideIn{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}`;
  document.head.appendChild(style);
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function setButtonLoading(btn, loading, originalText) {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.textContent = "Please wait…";
  } else {
    btn.disabled = false;
    btn.textContent = originalText || btn.dataset.originalText;
  }
}

// ── Nav cart count (auto-init on pages where #cartCount exists) ───────────────
async function refreshNavCartCount() {
  const el = document.getElementById("cartCount");
  if (!el) return;

  if (!Auth.isLoggedIn()) {
    el.textContent = "0";
    return;
  }

  try {
    const cart = await CartAPI.get();
    el.textContent = cart.item_count;
  } catch (_) {
    el.textContent = "0";
  }
}

// Run on every page load
document.addEventListener("DOMContentLoaded", () => {
  refreshNavCartCount();

  // Show/hide Sign In vs user name in nav
  const signinLink = document.querySelector(".nav-signin-link");
  const userGreet  = document.querySelector(".nav-user-greet");
  if (signinLink && userGreet) {
    const user = Auth.getUser();
    if (user) {
      signinLink.style.display = "none";
      userGreet.style.display  = "inline";
      userGreet.textContent    = user.first_name || user.email;
    }
  }
});
