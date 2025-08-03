import { useState, useEffect } from "react";
import { predict } from "../services/api";
import RiskDisplay from "./RiskDisplay";
import HealthBadge from "./HealthBadge";

const DEFAULTS = {
  restart_count_last_5m: 0,
  cpu_usage_pct: 10,
  memory_usage_bytes: 50 * 1024 * 1024,
  ready_replica_ratio: 1.0,
  unavailable_replicas: 0,
  network_receive_bytes_per_s: 0,
  http_5xx_error_rate: 0.0,
};

const clamp = (name, v) => {
  if (name === "cpu_usage_pct") return Math.min(Math.max(v, 0), 100);
  if (name === "ready_replica_ratio") return Math.min(Math.max(v, 0), 1);
  return Math.max(v, 0);
};

export default function PredictionForm() {
  const [inputs, setInputs] = useState(() => {
    const stored = localStorage.getItem("lastInputs");
    return stored ? JSON.parse(stored) : DEFAULTS;
  });
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // Persist
  useEffect(() => {
    localStorage.setItem("lastInputs", JSON.stringify(inputs));
  }, [inputs]);

  const handleChange = (field) => (e) => {
    let value = parseFloat(e.target.value);
    if (isNaN(value)) value = 0;
    setInputs((i) => ({ ...i, [field]: clamp(field, value) }));
  };

  const validate = () => {
    if (inputs.cpu_usage_pct < 0 || inputs.cpu_usage_pct > 100) {
      return "cpu_usage_pct must be between 0 and 100";
    }
    if (inputs.ready_replica_ratio < 0 || inputs.ready_replica_ratio > 1) {
      return "ready_replica_ratio must be between 0 and 1";
    }
    // other fields non-negative
    return null;
  };

  const submit = async () => {
    setError(null);
    setResult(null);
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setLoading(true);
    try {
      const resp = await predict(inputs);
      setResult(resp);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto p-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Failure Risk Predictor</h1>
        <HealthBadge />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Object.entries(inputs).map(([k, v]) => (
          <div key={k} className="flex flex-col">
            <label className="font-medium mb-1">{k.replace(/_/g, " ")}</label>
            <input
              type="number"
              value={v}
              onChange={handleChange(k)}
              className="border rounded p-2"
              step={k === "ready_replica_ratio" ? 0.01 : "any"}
              min={0}
              max={k === "cpu_usage_pct" ? 100 : undefined}
            />
          </div>
        ))}
      </div>

      {error && (
        <div className="text-red-600 bg-red-100 p-2 rounded">
          Error: {error}
        </div>
      )}

      <div className="flex gap-4 items-center">
        <button
          onClick={submit}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        >
          {loading ? "Predicting..." : "Predict Risk"}
        </button>
        {result && <RiskDisplay result={result} />}
      </div>

      {result && (
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 border rounded">
            <h2 className="font-semibold mb-2">Details</h2>
            <div>Probability: {(result.probability * 100).toFixed(2)}%</div>
            <div>Risk: {result.risk}</div>
            <div>Model loaded: {String(result.model_loaded)}</div>
            {result.model_error && (
              <div className="text-sm text-yellow-700">
                Model error: {result.model_error}
              </div>
            )}
          </div>
          <div className="p-4 border rounded">
            <h2 className="font-semibold mb-2">Features (echoed)</h2>
            <pre className="text-xs">{JSON.stringify(result.features, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
