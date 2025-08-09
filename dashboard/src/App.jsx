import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const FEATURE_CONFIG = [
  { key: "restart_count_last_5m", label: "Restarts (last 5m)", type: "number", min: 0, step: 1, helper: "Number of restarts in the last 5 minutes" },
  { key: "cpu_usage_pct", label: "CPU Usage (%)", type: "number", min: 0, max: 100, step: 0.1, helper: "Percentage of CPU used" },
  { key: "memory_usage_bytes", label: "Memory Usage (bytes)", type: "number", min: 0, step: 1, helper: "Current memory usage in bytes" },
  { key: "ready_replica_ratio", label: "Ready Replica Ratio", type: "number", min: 0, max: 1, step: 0.01, helper: "Fraction of replicas ready (0 to 1)" },
  { key: "unavailable_replicas", label: "Unavailable Replicas", type: "number", min: 0, step: 1, helper: "Count of unavailable replicas" },
  { key: "network_receive_bytes_per_s", label: "Network Receive (bytes/s)", type: "number", min: 0, step: 1, helper: "Inbound network throughput" },
  { key: "http_5xx_error_rate", label: "HTTP 5xx Error Rate", type: "number", min: 0, step: 0.001, helper: "Rate of server errors (req/s)" },
];

const presets = {
  Normal: {
    restart_count_last_5m: 0,
    cpu_usage_pct: 18,
    memory_usage_bytes: 180 * 1024 * 1024,
    ready_replica_ratio: 1.0,
    unavailable_replicas: 0,
    network_receive_bytes_per_s: 12000,
    http_5xx_error_rate: 0.0,
  },
  "CPU Spike": {
    restart_count_last_5m: 0,
    cpu_usage_pct: 86,
    memory_usage_bytes: 350 * 1024 * 1024,
    ready_replica_ratio: 1.0,
    unavailable_replicas: 0,
    network_receive_bytes_per_s: 21000,
    http_5xx_error_rate: 0.0,
  },
  "Errors Surge": {
    restart_count_last_5m: 1,
    cpu_usage_pct: 35,
    memory_usage_bytes: 220 * 1024 * 1024,
    ready_replica_ratio: 0.92,
    unavailable_replicas: 1,
    network_receive_bytes_per_s: 16000,
    http_5xx_error_rate: 3.5,
  },
  "Unhealthy Replicas": {
    restart_count_last_5m: 3,
    cpu_usage_pct: 22,
    memory_usage_bytes: 260 * 1024 * 1024,
    ready_replica_ratio: 0.6,
    unavailable_replicas: 2,
    network_receive_bytes_per_s: 9000,
    http_5xx_error_rate: 0.4,
  },
};

const clamp = (n, min, max) => Math.max(min, Math.min(max ?? Number.POSITIVE_INFINITY, n));
const prettifyBytes = (v) => {
  if (v == null || isNaN(v)) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let n = Number(v);
  let u = 0;
  while (n >= 1024 && u < units.length - 1) { n /= 1024; u++; }
  return `${n.toFixed(n < 10 ? 2 : 1)} ${units[u]}`;
};

export default function App() {
  const [apiBase, setApiBase] = useState(() => localStorage.getItem("apiBase") || DEFAULT_API_BASE);
  const [form, setForm] = useState(() => {
    const saved = localStorage.getItem("form");
    return saved ? JSON.parse(saved) : { ...presets.Normal };
  });
  const [resp, setResp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [history, setHistory] = useState([]); // [{ts, prob, risk}]
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [intervalSec, setIntervalSec] = useState(10);
  const timerRef = useRef(null);

  useEffect(() => localStorage.setItem("apiBase", apiBase), [apiBase]);
  useEffect(() => localStorage.setItem("form", JSON.stringify(form)), [form]);

  useEffect(() => {
    const onKey = (e) => { if (e.key.toLowerCase() === "p") predict(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase, form]);

  useEffect(() => {
    if (!autoRefresh) { if (timerRef.current) clearInterval(timerRef.current); return; }
    timerRef.current = setInterval(() => { predict(); }, clamp(intervalSec, 3, 120) * 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, intervalSec, apiBase, form]);

  const onChange = (k) => (e) => {
    const v = e.target.value;
    setForm((f) => ({ ...f, [k]: v === "" ? "" : Number(v) }));
  };

  const applyPreset = (name) => {
    setForm({ ...presets[name] });
    setErr("");
  };

  const validate = () => {
    for (const f of FEATURE_CONFIG) {
      const v = form[f.key];
      if (v === "" || v == null || Number.isNaN(Number(v))) return `${f.label} is required.`;
      if (typeof f.min === "number" && v < f.min) return `${f.label} must be ≥ ${f.min}.`;
      if (typeof f.max === "number" && v > f.max) return `${f.label} must be ≤ ${f.max}.`;
    }
    return null;
  };

  const predict = async () => {
    const problem = validate();
    if (problem) { setErr(problem); return; }

    setLoading(true);
    setErr("");
    setResp(null);
    try {
      const r = await fetch(`${apiBase}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(`HTTP ${r.status}: ${text || r.statusText}`);
      const data = JSON.parse(text);
      setResp(data);
      if (typeof data?.probability === "number") {
        setHistory((h) => [...h, { ts: Date.now(), prob: data.probability, risk: data.risk }].slice(-60));
      }
    } catch (e) {
      setErr(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  const fetchSample = async () => {
    try {
      const r = await fetch(`${apiBase}/predict/sample`);
      if (!r.ok) return;
      const data = await r.json();
      setForm((f) => ({ ...f, ...data }));
    } catch {/* ignore */}
  };

  const riskColor = (risk) => (risk === "HIGH" ? "#f87171" : "#22c55e");
  const riskBg = (risk) => (risk === "HIGH" ? "rgba(248,113,113,.14)" : "rgba(34,197,94,.14)");

  const latestProb = resp?.probability ?? (history.length ? history[history.length - 1].prob : 0);
  const latestRisk = resp?.risk ?? (history.length ? history[history.length - 1].risk : "LOW");

  const gauge = useMemo(() => {
    const pct = clamp(Number(latestProb) * 100, 0, 100);
    const r = 60, c = 2 * Math.PI * r, filled = (pct / 100) * c;
    return { pct, r, c, filled };
  }, [latestProb]);

  const historyPath = useMemo(() => {
    if (!history.length) return "";
    const W = 320, H = 80;
    const maxPoints = Math.min(history.length, 60);
    const slice = history.slice(-maxPoints);
    const step = W / Math.max(1, slice.length - 1);
    const points = slice.map((d, i) => `${i * step},${H - d.prob * H}`);
    return `M ${points[0]} L ${points.slice(1).join(" ")}`;
  }, [history]);

  const copyJson = async () => {
    if (!resp) return;
    try { await navigator.clipboard.writeText(JSON.stringify(resp, null, 2)); } catch {/* ignore */}
  };

  return (
    <div className="container">
      <header className="topbar">
        <div className="brand"><span className="dot" />AI-DevOps Risk Dashboard</div>
        <div className="api">
          <label>API</label>
          <input
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            placeholder="http://localhost:5000"
            spellCheck={false}
            aria-label="API base URL"
          />
          <button className="btn ghost" onClick={fetchSample} title="Load sample payload">
            Load sample
          </button>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <div className="section-title">Signals</div>
          <div className="fields">
            {FEATURE_CONFIG.map((f) => (
              <div key={f.key} className="field">
                <label className="label" htmlFor={f.key}>{f.label}</label>
                <input
                  id={f.key}
                  type={f.type}
                  value={form[f.key]}
                  onChange={onChange(f.key)}
                  min={f.min}
                  max={f.max}
                  step={f.step}
                  disabled={loading}
                  aria-label={f.label}
                />
                <small className="helper">
                  {f.key === "memory_usage_bytes"
                    ? `${f.helper} (${prettifyBytes(form[f.key])})`
                    : f.helper}
                </small>
              </div>
            ))}
          </div>

          <div className="presets">
            <div className="section-subtitle">Presets</div>
            <div className="chips">
              {Object.keys(presets).map((p) => (
                <button key={p} className="chip" onClick={() => applyPreset(p)} disabled={loading}>{p}</button>
              ))}
              <button className="chip ghost" onClick={() => applyPreset("Normal")} disabled={loading}>Reset</button>
            </div>
          </div>

          <div className="controls">
            <button className="btn primary" onClick={predict} disabled={loading}>
              {loading ? "Predicting…" : "Predict"}
            </button>

            <label className="toggle">
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
              <span>Auto refresh</span>
            </label>

            <div className="interval">
              <label>every</label>
              <input
                type="number"
                min={3}
                max={120}
                step={1}
                value={intervalSec}
                onChange={(e) => setIntervalSec(Number(e.target.value || 10))}
              />
              <span>sec</span>
            </div>
          </div>

          {!!err && <div className="alert"><strong>Error:</strong> {err}</div>}
        </section>

        <section className="panel">
          <div className="cards">
            <div className="card gauge">
              <div className="section-title">Risk</div>
              <div className="gwrap">
                <svg viewBox="0 0 160 160" width="180" height="180" role="img" aria-label="Probability gauge">
                  <circle cx="80" cy="80" r={gauge.r} className="track" />
                  <circle
                    cx="80" cy="80" r={gauge.r}
                    className="progress"
                    style={{
                      strokeDasharray: `${gauge.c}px`,
                      strokeDashoffset: `${gauge.c - gauge.filled}px`,
                      stroke: riskColor(latestRisk),
                    }}
                  />
                </svg>
                <div className="gcenter">
                  <div className="gvalue">{(latestProb ?? 0).toFixed(3)}</div>
                  <div className="grisk" style={{ color: riskColor(latestRisk), background: riskBg(latestRisk) }}>
                    {latestRisk || "LOW"}
                  </div>
                </div>
              </div>
              <div className="mini">
                <div><div className="k">CPU</div><div className="v">{clamp(Number(form.cpu_usage_pct), 0, 100).toFixed(1)}%</div></div>
                <div><div className="k">Memory</div><div className="v">{prettifyBytes(form.memory_usage_bytes)}</div></div>
                <div><div className="k">5xx</div><div className="v">{Number(form.http_5xx_error_rate).toFixed(2)}/s</div></div>
                <div><div className="k">Ready</div><div className="v">{Number(form.ready_replica_ratio).toFixed(2)}</div></div>
              </div>
            </div>

            <div className="card history">
              <div className="section-title">Probability (last {history.length || 0})</div>
              <div className="spark">
                <svg viewBox="0 0 320 80" width="100%" height="80">
                  <path d={historyPath} className="sparkline" />
                </svg>
              </div>
              <div className="legend">
                <span className="dot ok" /> Low risk
                <span className="spacer" />
                <span className="dot hi" /> High risk
              </div>
            </div>

            <div className="card raw">
              <div className="section-title">Response</div>
              {resp ? (
                <>
                  <pre className="code" aria-live="polite">{JSON.stringify(resp, null, 2)}</pre>
                  <div className="actions">
                    <button className="btn" onClick={copyJson}>Copy JSON</button>
                    <details className="details">
                      <summary>Why “Heuristic”?</summary>
                      <p>If the backend couldn’t load a model file, it falls back to a heuristic.
                        Ensure <code>MODEL_PATH</code> is valid in your container.</p>
                    </details>
                  </div>
                </>
              ) : (
                <div className="placeholder">Run a prediction to see the response here.</div>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="foot">
        <span>Backend: <code>{apiBase}</code></span>
        <span className="sep">•</span>
        <span>Press <kbd>P</kbd> to predict</span>
      </footer>

      <style>{`
        :root{
          --bg:#0b1220; --surface:#101a2e; --surface2:#0f1627; --border:#223357;
          --text:#e6eefc; --muted:#99a7c2; --brand:#4f8bff;
          --ok:#22c55e; --okbg:rgba(34,197,94,.14);
          --hi:#f87171; --hibg:rgba(248,113,113,.14);
          --radius:16px; --shadow:0 10px 30px rgba(0,0,0,.35);
        }
        *{box-sizing:border-box}
        html,body,#root{height:100%}
        body{margin:0;background:radial-gradient(1200px 600px at 20% -10%, #182744 0%, transparent 60%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica Neue,Arial}
        .container{max-width:1200px;margin:24px auto;padding:0 16px 48px}
        .topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
        .brand{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.2px}
        .dot{width:10px;height:10px;border-radius:50%;background:var(--brand);box-shadow:0 0 16px var(--brand)}
        .api{display:flex;align-items:center;gap:10px}
        .api input{width:360px;max-width:48vw;background:var(--surface);border:1px solid var(--border);padding:10px 12px;color:var(--text);border-radius:10px;outline:none}
        .api input:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(79,139,255,.2)}
        .grid{display:grid;grid-template-columns:460px 1fr;gap:16px}
        @media (max-width:980px){.grid{grid-template-columns:1fr}}
        .panel{background:linear-gradient(180deg,var(--surface),var(--surface2));border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:18px}
        .section-title{font-size:13px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin:0 0 10px}
        .section-subtitle{font-size:12px;color:var(--muted);margin-top:8px}
        .fields{display:grid;gap:12px;grid-template-columns:repeat(2,minmax(160px,1fr))}
        @media (max-width:520px){.fields{grid-template-columns:1fr}}
        .field{display:flex;flex-direction:column;gap:6px}
        .label{font-size:12px;color:var(--muted)}
        input[type="number"]{width:100%;background:#0c1427;border:1px solid var(--border);color:var(--text);padding:12px;border-radius:10px;outline:none}
        input[type="number"]:focus{border-color:var(--brand);box-shadow:0 0 0 3px rgba(79,139,255,.18)}
        .helper{font-size:11.5px;color:var(--muted)}
        .presets .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
        .chip{background:#0d1a31;border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:999px;cursor:pointer;transition:transform .1s ease,border-color .2s ease}
        .chip:hover{transform:translateY(-1px);border-color:var(--brand)}
        .chip.ghost{opacity:.8}
        .controls{display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap}
        .btn{background:var(--brand);color:#fff;border:none;padding:10px 16px;border-radius:12px;cursor:pointer;font-weight:700;box-shadow:0 8px 18px rgba(79,139,255,.25)}
        .btn.primary{background:linear-gradient(180deg,#6ea8fe,#4f8bff)}
        .btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text)}
        .btn:disabled{opacity:.7;cursor:not-allowed}
        .toggle{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
        .interval{display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}
        .interval input{width:70px;background:#0c1427;border:1px solid var(--border);color:var(--text);padding:8px 10px;border-radius:8px}
        .alert{margin-top:12px;background:var(--hibg);border:1px solid rgba(248,113,113,.35);color:#ffb4b4;padding:10px 12px;border-radius:10px}
        .cards{display:grid;gap:16px}
        .card{background:#0c1427;border:1px solid var(--border);border-radius:14px;padding:16px}
        .card.gauge{display:flex;flex-direction:column;gap:8px}
        .gwrap{position:relative;width:180px;height:180px;margin:8px 0 6px}
        .track{fill:none;stroke:#132344;stroke-width:12;opacity:.8}
        .progress{fill:none;stroke-width:12;stroke-linecap:round;transform:rotate(-90deg);transform-origin:80px 80px;transition:stroke-dashoffset .4s ease}
        .gcenter{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
        .gvalue{font-weight:800;font-size:30px;letter-spacing:.5px}
        .grisk{display:inline-block;margin-top:6px;padding:4px 10px;border-radius:999px;font-weight:700;font-size:13px}
        .mini{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:6px}
        .mini .k{color:var(--muted);font-size:12px}
        .mini .v{font-weight:700}
        .card.history .spark{background:#0a1122;border-radius:10px;padding:6px;border:1px solid var(--border)}
        .sparkline{fill:none;stroke:#6ea8fe;stroke-width:2;filter:drop-shadow(0 1px 3px rgba(110,168,254,.5))}
        .legend{display:flex;align-items:center;gap:10px;color:var(--muted);font-size:12px;margin-top:8px}
        .legend .dot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px}
        .legend .dot.ok{background:var(--ok)}
        .legend .dot.hi{background:var(--hi)}
        .legend .spacer{flex:1}
        .card.raw .code{max-height:260px;overflow:auto;background:#0a1122;padding:12px;border-radius:10px;border:1px solid var(--border);font-size:12.5px}
        .placeholder{color:var(--muted);padding:8px 0}
        .actions{display:flex;gap:10px;align-items:center;margin-top:10px}
        .foot{margin-top:16px;display:flex;gap:12px;align-items:center;color:var(--muted);font-size:12.5px}
        .sep{opacity:.4}
        kbd{background:#15213b;border:1px solid var(--border);padding:2px 6px;border-radius:6px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}
      `}</style>
    </div>
  );
}
