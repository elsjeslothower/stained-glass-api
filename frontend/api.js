// Shared fetch helper + API base configuration. No build step by design —
// this is a thin scaffold over the API, not a product frontend (see README).

const DEFAULT_API_BASE = "http://127.0.0.1:8000";

function getApiBase() {
  return localStorage.getItem("apiBase") || DEFAULT_API_BASE;
}

function setApiBase(url) {
  localStorage.setItem("apiBase", url.replace(/\/+$/, ""));
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : JSON.stringify(body);
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new Error(`${res.status} ${detail}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Redirects to the login page if there's no valid session. Call at the top
// of every protected page's startup script.
async function requireAuth() {
  try {
    await apiFetch("/auth/me");
    return true;
  } catch {
    location.href = "login.html";
    return false;
  }
}

async function logout() {
  try {
    await apiFetch("/auth/logout", { method: "POST" });
  } finally {
    location.href = "login.html";
  }
}

// Wires up the "API base" input that appears in the header of every page.
function initApiBaseControl() {
  const input = document.getElementById("api-base-input");
  if (!input) return;
  input.value = getApiBase();
  input.addEventListener("change", () => {
    setApiBase(input.value || DEFAULT_API_BASE);
    input.value = getApiBase();
    location.reload();
  });
}

// Wires up the "Log out" link that appears in the header of protected pages.
function initLogoutControl() {
  const link = document.getElementById("logout-link");
  if (!link) return;
  link.addEventListener("click", (e) => {
    e.preventDefault();
    logout();
  });
}

function money(value) {
  if (value === null || value === undefined) return "—";
  return `$${Number(value).toFixed(2)}`;
}

function statusBadgeClasses(status) {
  return `badge badge-${status || "draft"}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
  initApiBaseControl();
  initLogoutControl();
});
