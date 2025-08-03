// dashboard/src/api.js
const API_BASE =
  (typeof window !== "undefined" && window.__API_BASE__) ||
  import.meta.env.VITE_API_BASE ||
  "http://localhost:5000";

export async function predict(payload) {
  const res = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Predict failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function healthz() {
  const res = await fetch(`${API_BASE}/healthz`);
  if (!res.ok) throw new Error(`Health failed: ${res.status}`);
  return res.json();
}
