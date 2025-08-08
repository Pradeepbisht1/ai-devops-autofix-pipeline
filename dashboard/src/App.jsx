import React, { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const FEATURE_CONFIG = [
  {
    key: "restart_count_last_5m",
    label: "Restarts (last 5m)",
    type: "number",
    min: 0,
    step: 1,
    helper: "Number of restarts in the last 5 minutes",
  },
  {
    key: "cpu_usage_pct",
    label: "CPU Usage (%)",
    type: "number",
    min: 0,
    max: 100,
    step: 0.1,
    helper: "Percentage of CPU used",
  },
  {
    key: "memory_usage_bytes",
    label: "Memory Usage (bytes)",
    type: "number",
    min: 0,
    step: 1,
    helper: "Current memory usage in bytes",
  },
  {
    key: "ready_replica_ratio",
    label: "Ready Replica Ratio",
    type: "number",
    min: 0,
    max: 1,
    step: 0.01,
    helper: "Fraction of replicas ready (0 to 1)",
  },
  {
    key: "unavailable_replicas",
    label: "Unavailable Replicas",
    type: "number",
    min: 0,
    step: 1,
    helper: "Count of unavailable replicas",
  },
  {
    key: "network_receive_bytes_per_s",
    label: "Network Receive (bytes/s)",
    type: "number",
    min: 0,
    step: 1,
    helper: "Inbound network throughput",
  },
  {
    key: "http_5xx_error_rate",
    label: "HTTP 5xx Error Rate",
    type: "number",
    min: 0,
    step: 0.001,
    helper: "Rate of server errors",
  },
];

export default function App() {
  const [form, setForm] = useState({
    restart_count_last_5m: 0,
    cpu_usage_pct: 10,
    memory_usage_bytes: 50 * 1024 * 1024,
    ready_replica_ratio: 1.0,
    unavailable_replicas: 0,
    network_receive_bytes_per_s: 0,
    http_5xx_error_rate: 0.0,
  });
  const [resp, setResp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const onChange = (k) => (e) => {
    const v = e.target.value;
    setForm((f) => ({ ...f, [k]: v === "" ? "" : Number(v) }));
  };

  const predict = async () => {
    setLoading(true);
    setErr("");
    setResp(null);
    try {
      const r = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!r.ok) {
        const text = await r.text();
        throw new Error(`HTTP ${r.status}: ${text}`);
      }
      const data = await r.json();
      setResp(data);
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const riskColor = (risk) => (risk === "HIGH" ? "#f87171" : "#22c55e");

  return (
    <div className="container">
      <header>
        <h1>AI-DevOps Pridict Risk Dashboard</h1>
        <p className="sub">Backend: <code>{API_BASE}</code></p>
      </header>

      <section className="card grid">
        {FEATURE_CONFIG.map((f) => (
          <div key={f.key} className="field">
            <label className="label">{f.label}</label>
            <input
              type={f.type}
              value={form[f.key]}
              onChange={onChange(f.key)}
              min={f.min}
              max={f.max}
              step={f.step}
              disabled={loading}
              aria-label={f.label}
            />
            <small className="helper">{f.helper}</small>
          </div>
        ))}
      </section>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <button className="btn" onClick={predict} disabled={loading}>
          {loading ? "Predicting..." : "Predict"}
        </button>
        {resp && (
          <div className="result-card">
            <div className="result-row">
              <div>
                <div className="title">Probability</div>
                <div className="value">{resp.probability?.toFixed(6)}</div>
              </div>
              <div>
                <div className="title">Risk</div>
                <div
                  className="badge"
                  style={{ background: riskColor(resp.risk), color: "#fff" }}
                >
                  {resp.risk}
                </div>
              </div>
            </div>
            <div className="details-toggle">
              <details>
                <summary>Show full response</summary>
                <pre>{JSON.stringify(resp, null, 2)}</pre>
              </details>
            </div>
          </div>
        )}
      </div>

      {err && <div className="error">Error: {err}</div>}

      <footer>
        <small>Powered by your ML risk API. Adjust inputs to simulate real-time signals.</small>
      </footer>

      <style jsx>{`
        .container {
          max-width: 1000px;
          margin: 40px auto;
          padding: 0 16px;
          font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
            Roboto, "Helvetica Neue", Arial, sans-serif;
          color: #e5e7eb;
          background: #0f172a;
          min-height: 100vh;
        }
        header h1 {
          margin: 0;
          font-size: 2rem;
        }
        .sub {
          margin: 4px 0 24px;
          color: #94a3b8;
        }
        .card {
          background: #1e2a44;
          padding: 20px 24px;
          border-radius: 14px;
          margin-bottom: 16px;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 16px;
        }
        .field {
          display: flex;
          flex-direction: column;
        }
        .label {
          font-size: 0.75rem;
          letter-spacing: 1px;
          text-transform: uppercase;
          margin-bottom: 6px;
          font-weight: 600;
        }
        input {
          background: #0f1f44;
          border: 1px solid #334a7f;
          padding: 12px 14px;
          border-radius: 8px;
          font-size: 1rem;
          color: #f1f5fe;
        }
        .helper {
          margin-top: 4px;
          font-size: 0.65rem;
          color: #94a3b8;
        }
        .btn {
          background: #22c55e;
          border: none;
          padding: 12px 24px;
          border-radius: 10px;
          font-size: 1rem;
          cursor: pointer;
          font-weight: 600;
          color: #fff;
          transition: filter .2s;
        }
        .btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        .btn:hover:not(:disabled) {
          filter: brightness(1.05);
        }
        .result-card {
          background: #1f2f55;
          border: 1px solid #334a7f;
          border-radius: 14px;
          padding: 16px 20px;
          margin-top: 8px;
          min-width: 320px;
          color: #f0f8ff;
        }
        .result-row {
          display: flex;
          gap: 40px;
          flex-wrap: wrap;
        }
        .title {
          font-size: 0.7rem;
          text-transform: uppercase;
          letter-spacing: 1px;
          margin-bottom: 4px;
          color: #94a3b8;
        }
        .value {
          font-size: 1.4rem;
          font-weight: 700;
        }
        .badge {
          display: inline-block;
          padding: 6px 14px;
          border-radius: 999px;
          font-weight: 700;
          font-size: 1rem;
          margin-top: 4px;
        }
        .details-toggle {
          margin-top: 12px;
        }
        pre {
          background: #0e1d3a;
          padding: 12px;
          border-radius: 8px;
          overflow: auto;
          font-size: 0.75rem;
          max-height: 300px;
        }
        .error {
          margin-top: 12px;
          background: #f87171;
          padding: 10px 16px;
          border-radius: 8px;
          color: #fff;
          font-weight: 600;
        }
        footer {
          margin-top: 60px;
          font-size: 0.65rem;
          color: #94a3b8;
          text-align: center;
        }
      `}</style>
    </div>
  );
}
