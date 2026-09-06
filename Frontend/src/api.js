const BASE = import.meta.env.VITE_BACKEND_API_URL || "/api";

function token() {
  return localStorage.getItem("accessToken");
}

function query(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      q.set(key, value);
    }
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

export async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (token()) {
    headers.Authorization = `Bearer ${token()}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail) ? detail[0]?.msg : detail;
    if (res.status === 405 || message === "Method Not Allowed") {
      throw new Error("");
    }
    throw new Error(typeof message === "string" && message ? message : "요청에 실패했습니다.");
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  signup: (body) => request("/auth/signup", { method: "POST", body: JSON.stringify(body) }),
  login: (body) => request("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request("/users/me"),
  updateMe: (body) => request("/users/me", { method: "PUT", body: JSON.stringify(body) }),
  business: () => request("/users/me/business-profile"),
  updateBusiness: (body) =>
    request("/users/me/business-profile", { method: "PUT", body: JSON.stringify(body) }),
  calendar: (year, month, type) => request(`/calendar${query({ year, month, type })}`),
  createEvent: (body) => request("/calendar", { method: "POST", body: JSON.stringify(body) }),
  deleteEvent: (id) => request(`/calendar/${id}`, { method: "DELETE" }),
  reminders: () => request("/tax/reminders"),
  createReminder: (body) =>
    request("/tax/reminders", { method: "POST", body: JSON.stringify(body) }),
  deleteReminder: (id) => request(`/tax/reminders/${id}`, { method: "DELETE" }),
  suggested: (category) => request(`/chat/categories/${category}/suggested-questions`),
  sendChat: (body) => request("/chat/messages", { method: "POST", body: JSON.stringify(body) }),
  chatHistory: (category) => request(`/chat/messages${query({ category })}`),
  clearChat: (category) => request(`/chat/messages${query({ category })}`, { method: "DELETE" }),
  sources: (id) => request(`/chat/messages/${id}/sources`),
  policies: (params = {}) => request(`/policies${query(params)}`),
  recommend: () => request("/policies/recommendations"),
  savedPolicies: () => request("/policies/saved"),
  policy: (id) => request(`/policies/${id}`),
  eligibility: (id) => request(`/policies/${id}/eligibility`),
  savePolicy: (id) => request(`/policies/${id}/save`, { method: "POST" }),
  announcementSummary: (id) => request(`/announcements/${id}/summary`),
  diagnose: (conditions) =>
    request("/tax/business-type/diagnosis", {
      method: "POST",
      body: JSON.stringify({ conditions }),
    }),
  taxInfo: () => request("/tax/info"),
  updateTaxInfo: (taxInfo) =>
    request("/tax/info", { method: "PUT", body: JSON.stringify({ taxInfo }) }),
  taxReduction: () => request("/tax/tax-reduction/check", { method: "POST" }),
  taxReductionResult: () => request("/tax/tax-reduction/result"),
  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("image", file);
    return request("/expenses/receipts", { method: "POST", body: form });
  },
  receipt: (id) => request(`/expenses/receipts/${id}`),
  expenses: () => request("/expenses"),
  updateExpense: (id, body) =>
    request(`/expenses/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deductibility: (id) => request(`/expenses/${id}/deductibility`),
  deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" }),
  adminLogin: (body) => request("/admin/auth/login", { method: "POST", body: JSON.stringify(body) }),
  adminMonitoring: () => request("/admin/monitoring"),
  adminUsers: (page = 1) => request(`/admin/users${query({ page })}`),
  adminUser: (id) => request(`/admin/users/${id}`),
  adminUpdateUser: (id, body) =>
    request(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  adminTaxDocuments: () => request("/admin/tax-documents"),
  adminCreateTaxDocument: (body) =>
    request("/admin/tax-documents", { method: "POST", body: JSON.stringify(body) }),
  adminPolicies: () => request("/admin/policies"),
  adminCreatePolicy: (body) =>
    request("/admin/policies", { method: "POST", body: JSON.stringify(body) }),
  adminAnnouncements: () => request("/admin/announcements"),
  adminCreateAnnouncement: (body) =>
    request("/admin/announcements", { method: "POST", body: JSON.stringify(body) }),
  adminReindex: () => request("/admin/rag-documents/reindex", { method: "POST", body: JSON.stringify({}) }),
  notifications: () => request("/notifications"),
  readNotification: (id) => request(`/notifications/${id}/read`, { method: "POST", body: JSON.stringify({}) }),
  readAllNotifications: () => request("/notifications/read-all", { method: "POST", body: JSON.stringify({}) }),
  pushNotification: (eventId) =>
    request("/notifications/push", { method: "POST", body: JSON.stringify({ eventId }) }),
};
