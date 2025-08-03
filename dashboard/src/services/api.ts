// services/api.ts
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";
const TIMEOUT_MS = 10000;

export interface PredictPayload {
  restart_count_last_5m: number;
  cpu_usage_pct: number;
  memory_usage_bytes: number;
  ready_replica_ratio: number;
  unavailable_replicas: number;
  network_receive_bytes_per_s: number;
  http_5xx_error_rate: number;
}

export interface PredictResponse {
  ok: boolean;
  probability: number;
  risk: "HIGH" | "LOW";
  features: Record<string, number>;
  model_loaded: boolean;
  model_error: string | null;
}

export interface HealthResponse {
  ok: boolean;
  status: string;
  model_loaded: boolean;
  model_error: string | null;
  model_path: string;
  model_path_exists: boolean;
  sklearn_version?: string;
}

async function requestJson(input: RequestInfo, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(input, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`HTTP ${res.status}: ${body}`);
    }
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export function predict(payload: PredictPayload): Promise<PredictResponse> {
  return requestJson(`${API_BASE}/predict`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchHealth(): Promise<HealthResponse> {
  return requestJson(`${API_BASE}/healthz`);
}
