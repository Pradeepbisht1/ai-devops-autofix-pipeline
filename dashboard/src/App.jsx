import React, { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Activity, Gauge, Server, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

// --- Config ---
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:5000";
const DEFAULT_FEATURES = {
  restart_count_last_5m: 0,
  cpu_usage_pct: 10,
  memory_usage_bytes: 50 * 1024 * 1024,
  ready_replica_ratio: 1.0,
  unavailable_replicas: 0,
  network_receive_bytes_per_s: 0,
  http_5xx_error_rate: 0,
};

// --- Small 3D scene ---
function SpinningGem() {
  return (
    <Canvas className="h-40 w-full" camera={{ position: [2.8, 2.4, 3.2], fov: 55 }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[3, 3, 2]} intensity={1.1} />
      <mesh rotation={[0.5, 0.2, 0.1]}> 
        <icosahedronGeometry args={[1.2, 0]} />
        <meshStandardMaterial metalness={0.6} roughness={0.15} />
      </mesh>
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={1.2} />
    </Canvas>
  );
}

export default function App() {
  const [health, setHealth] = useState("unknown");
  const [prob, setProb] = useState(null);
  const [loading, setLoading] = useState(false);
  const [features, setFeatures] = useState(DEFAULT_FEATURES);
  const [threshold, setThreshold] = useState(0.6);
  const [err, setErr] = useState("");

  const radialData = useMemo(
    () => [{ name: "prob", value: Math.round((prob ?? 0) * 100) }],
    [prob]
  );

  const highRisk = prob != null && prob > threshold;

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/healthz`);
        setHealth(r.ok ? "ok" : "down");
      } catch {
        setHealth("down");
      }
    })();
  }, []);

  async function doPredict() {
    setLoading(true); setErr("");
    try {
      const r = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(features),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const js = await r.json();
      const p = js.prob ?? js.y ?? 0; // supports current dummy as well
      setProb(Number(p));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  function update(k, v) {
    setFeatures((f) => ({ ...f, [k]: v }));
  }

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100 p-6">
      <div className="mx-auto max-w-6xl grid gap-6 md:grid-cols-3">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="md:col-span-3">
          <h1 className="text-2xl md:text-3xl font-semibold flex items-center gap-3">
            <Activity className="h-6 w-6" /> AI‑DevOps Demo Dashboard
          </h1>
          <p className="text-sm text-slate-300 mt-1">Predict failure probability, check health, and view live metrics.</p>
        </motion.div>

        {/* Health + 3D */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="bg-slate-900/60 backdrop-blur border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Server className="h-5 w-5" />
                  <div>
                    <div className="text-sm text-slate-300">Backend Health</div>
                    <div className={`text-lg font-medium ${health === "ok" ? "text-emerald-400" : "text-rose-400"}`}>
                      {health === "ok" ? "OK" : "DOWN"}
                    </div>
                  </div>
                </div>
                <Button size="sm" variant="secondary" onClick={() => window.location.reload()}>
                  <RefreshCw className="h-4 w-4 mr-1"/> Refresh
                </Button>
              </div>
              <div className="mt-3 rounded-2xl overflow-hidden ring-1 ring-slate-700">
                <SpinningGem />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Probability gauge */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card className="bg-slate-900/60 backdrop-blur border-slate-700">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="h-5 w-5" />
                <div className="text-sm text-slate-300">Failure Probability</div>
              </div>
              <div className="h-48 flex items-center justify-center">
                <RadialBarChart width={220} height={220} data={radialData} innerRadius="60%" outerRadius="100%" startAngle={180} endAngle={0}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={10} />
                </RadialBarChart>
              </div>
              <div className="text-center">
                <div className="text-3xl font-semibold">
                  {prob == null ? "--" : `${Math.round(prob * 100)}%`}
                </div>
                <div className={`text-sm ${highRisk ? "text-rose-400" : "text-emerald-400"}`}>
                  {prob == null ? "Tap Predict" : highRisk ? "HIGH RISK" : "OK"}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Feature form */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card className="bg-slate-900/60 backdrop-blur border-slate-700">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                <div className="text-sm text-slate-300">Input Features</div>
              </div>

              {Object.entries(features).map(([k, v]) => (
                <div key={k} className="grid grid-cols-3 items-center gap-2">
                  <label className="text-xs col-span-1 text-slate-300">{k}</label>
                  <Input
                    className="col-span-2 bg-slate-800 border-slate-700 text-slate-100"
                    type="number"
                    step="any"
                    value={v}
                    onChange={(e) => update(k, Number(e.target.value))}
                  />
                </div>
              ))}

              <div className="grid grid-cols-3 items-center gap-2">
                <label className="text-xs col-span-1 text-slate-300">threshold</label>
                <Input
                  className="col-span-2 bg-slate-800 border-slate-700 text-slate-100"
                  type="number"
                  step="0.01"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                />
              </div>

              <div className="flex gap-2">
                <Button disabled={loading} onClick={doPredict} className="w-full">
                  {loading ? "Predicting…" : "Predict"}
                </Button>
              </div>

              {err && <div className="text-xs text-rose-400">{err}</div>}
            </CardContent>
          </Card>
        </motion.div>

        {/* Footer / Tips */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="md:col-span-3 text-center text-xs text-slate-400">
          API: <code>{API_BASE}</code> · Try chaos: <code>FAILURE_INJECTION_PROB=0.1</code> · Rate limit: <code>RATE_LIMIT</code>
        </motion.div>
      </div>
    </div>
  );
}
