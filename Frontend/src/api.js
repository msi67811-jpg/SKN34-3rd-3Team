const BASE = "/api";

function token() {
  return localStorage.getItem("accessToken");
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
    throw new Error(message || "요청에 실패했습니다.");
  }
  return data;
}

export const api = {
  signup: (body) => request("/auth/signup", { method: "POST", body: JSON.stringify(body) }),
  login: (body) => request("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request("/users/me"),
  updateMe: (body) => request("/users/me", { method: "PUT", body: JSON.stringify(body) }),
  business: () => request("/users/me/business-profile"),
  updateBusiness: (body) =>
    request("/users/me/business-profile", { method: "PUT", body: JSON.stringify(body) }),
  calendar: (year, month, type) => {
    const q = new URLSearchParams();
    if (year) q.set("year", year);
    if (month) q.set("month", month);
    if (type) q.set("type", type);
    return request(`/calendar?${q}`);
  },
  reminders: () => request("/tax/reminders"),
  createReminder: (body) =>
    request("/tax/reminders", { method: "POST", body: JSON.stringify(body) }),
  deleteReminder: (id) => request(`/tax/reminders/${id}`, { method: "DELETE" }),
  suggested: (category) => request(`/chat/categories/${category}/suggested-questions`),
  sendChat: (body) => request("/chat/messages", { method: "POST", body: JSON.stringify(body) }),
  chatHistory: (category) => request(`/chat/messages${category ? `?category=${category}` : ""}`),
  sources: (id) => request(`/chat/messages/${id}/sources`),
  policies: (params = {}) => {
    const q = new URLSearchParams(params);
    return request(`/policies?${q}`);
  },
  recommend: () => request("/policies/recommendations"),
  policy: (id) => request(`/policies/${id}`),
  eligibility: (id) => request(`/policies/${id}/eligibility`),
  savePolicy: (id) => request(`/policies/${id}/save`, { method: "POST" }),
  savedPolicies: () => request("/policies/saved"),
  diagnose: (conditions) =>
    request("/tax/business-type/diagnosis", { method: "POST", body: JSON.stringify({ conditions }) }),
  taxReduction: () => request("/tax/tax-reduction/check", { method: "POST" }),
  uploadReceipt: (file) => {
    const form = new FormData();
    form.append("image", file);
    return request("/expenses/receipts", { method: "POST", body: form });
  },
  receipt: (id) => request(`/expenses/receipts/${id}`),
  expenses: () => request("/expenses"),
  deductibility: (id) => request(`/expenses/${id}/deductibility`),
};
