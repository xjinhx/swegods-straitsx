const BASE = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

export const api = {
  products: () => request("/products"),
  activityFeed: (limit = 50) => request(`/activity/feed?limit=${limit}`),
  orders: () => request("/merchant/orders"),
  agents: () => request("/merchant/agents"),
  rules: () => request("/merchant/rules"),
  createRule: (rule) => request("/merchant/rules", { method: "POST", body: JSON.stringify(rule) }),
  deleteRule: (id) => request(`/merchant/rules/${id}`, { method: "DELETE" }),
  override: (orderId, note) =>
    request(`/merchant/orders/${orderId}/override`, { method: "POST", body: JSON.stringify({ note }) }),
  orderAudit: (orderId) => request(`/audit/${orderId}`),
};
