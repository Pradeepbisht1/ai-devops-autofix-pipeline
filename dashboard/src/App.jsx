import React, { useEffect, useMemo, useState, useRef, Component, Suspense } from "react";
import { motion as m } from "framer-motion";
import { RadialBarChart, RadialBar, PolarAngleAxis } from "recharts";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
import * as THREE from "three";
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

// --- OrbitControls wrapper ---
import { OrbitControls as ThreeOrbitControls } from "three/examples/jsm/controls/OrbitControls";
function OrbitControlsWrapper() {
  const { camera, gl } = useThree();
  const controlsRef = useRef();
  useEffect(() => {
    controlsRef.current = new ThreeOrbitControls(camera, gl.domElement);
    controlsRef.current.enableZoom = false;
    controlsRef.current.autoRotate = true;
    controlsRef.current.autoRotateSpeed = 1.1;
    controlsRef.current.enableDamping = true;
    controlsRef.current.dampingFactor = 0.15;
    return () => controlsRef.current?.dispose();
  }, [camera, gl]);
  useFrame(() => controlsRef.current?.update());
  return null;
}

// --- Error boundary for 3D canvas ---
class CanvasErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || "Unknown error" };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-3 bg-rose-600 text-white rounded-md text-sm">
          3D render error: {this.state.message}
        </div>
      );
    }
    return this.props.children;
  }
}

// --- Robot-like pipeline 3D object ---
function RobotPipeline() {
  const ref = useRef();
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.rotation.y = Math.sin(clock.getElapsedTime() * 0.5) * 0.2;
      ref.current.position.y = Math.sin(clock.getElapsedTime() * 1) * 0.04;
    }
  });
  const curve = useMemo(() => {
    const pts = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0.2, 0.1, -0.3),
      new THREE.Vector3(0.4, -0.1, -0.6),
      new THREE.Vector3(0.6, 0, -0.9),
    ];
    return new THREE.CatmullRomCurve3(pts);
  }, []);
  const markerRef = useRef();
  const tRef = useRef(0);
  useFrame((_, delta) => {
    tRef.current = (tRef.current + delta * 0.2) % 1;
    const p = curve.getPoint(tRef.current);
    if (markerRef.current) markerRef.current.position.copy(p);
  });
  return (
    <group ref={ref} scale={0.8}>
      <mesh position={[0, -1, 0]}>
        <boxGeometry args={[3, 0.2, 2]} />
        <meshStandardMaterial color="#1f2a3a" metalness={0.3} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <cylinderGeometry args={[0.5, 0.5, 1.8, 20]} />
        <meshStandardMaterial color="#0ea5e9" metalness={0.6} roughness={0.3} />
      </mesh>
      {[-1.1, 1.1].map((x) => (
        <group key={x} position={[x, 0.2, 0]}>
          <mesh position={[0, -0.2, 0]}>
            <boxGeometry args={[0.3, 0.8, 0.3]} />
            <meshStandardMaterial color="#22d3ee" metalness={0.4} roughness={0.25} />
          </mesh>
          <mesh position={[0, -0.8, 0]}>
            <cylinderGeometry args={[0.15, 0.15, 0.4, 12]} />
            <meshStandardMaterial color="#f0f9ff" metalness={0.5} roughness={0.2} />
          </mesh>
        </group>
      ))}
      <mesh position={[0, 1.0, 0]}>
        <sphereGeometry args={[0.4, 16, 16]} />
        <meshStandardMaterial color="#7dd3fc" metalness={0.6} roughness={0.1} />
      </mesh>
      <mesh position={[-0.15, 1.05, 0.35]}>
        <sphereGeometry args={[0.07, 8, 8]} />
        <meshStandardMaterial emissive="#fcd34d" emissiveIntensity={1} color="#000" />
      </mesh>
      <mesh position={[0.15, 1.05, 0.35]}>
        <sphereGeometry args={[0.07, 8, 8]} />
        <meshStandardMaterial emissive="#fcd34d" emissiveIntensity={1} color="#000" />
      </mesh>
      <mesh position={[0, 0.4, -1.1]} rotation={[Math.PI / 2, 0, 0]}>
        <tubeGeometry args={[curve, 64, 0.05, 8, false]} />
        <meshStandardMaterial color="#38bdf8" metalness={0.3} roughness={0.4} />
      </mesh>
      <mesh ref={markerRef}>
        <sphereGeometry args={[0.06, 12, 12]} />
        <meshStandardMaterial emissive="#f47174" emissiveIntensity={1} color="#ffe4ec" />
      </mesh>
    </group>
  );
}

function SpinningGem() {
  return (
    <Canvas className="h-56 w-full" camera={{ position: [3, 2, 4], fov: 50 }}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 5, 3]} intensity={1.1} />
      <CanvasErrorBoundary>
        <Suspense fallback={null}>
          <RobotPipeline />
        </Suspense>
      </CanvasErrorBoundary>
      <OrbitControlsWrapper />
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

  const radialData = useMemo(() => [{ name: "prob", value: Math.round((prob ?? 0) * 100) }], [prob]);
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
    setLoading(true);
    setErr("");
    try {
      const r = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(features),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const js = await r.json();
      setProb(Number(js.prob ?? js.y ?? 0));
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  function update(k, v) {
    setFeatures((f) => ({ ...f, [k]: isNaN(v) ? 0 : Math.max(0, v) }));
  }
  function clampThreshold(val) {
    if (isNaN(val)) return 0;
    return Math.min(1, Math.max(0, val));
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-zinc-900 via-slate-900 to-slate-800 text-slate-100 px-4 py-10">
      <div className="w-full max-w-[1100px]">
        {/* Header centered */}
        <m.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8 flex flex-col items-center"
        >
          <div className="flex flex-col items-center gap-2">
            <div className="flex items-center gap-3 justify-center">
              <Activity className="h-8 w-8 text-teal-400" />
              <h1 className="text-4xl font-bold">AI-DevOps Dashboard</h1>
            </div>
            <p className="text-sm text-slate-300">Failure risk prediction &amp; backend health overview</p>
            <div className="mt-3 flex flex-wrap justify-center gap-3 text-xs">
              <div className="px-3 py-1 rounded bg-zinc-800 ring-1 ring-zinc-700">
                <span className="font-semibold">API:</span> <code>{API_BASE}</code>
              </div>
              <div className="px-3 py-1 rounded bg-zinc-800 ring-1 ring-zinc-700">
                <span className="font-semibold">Chaos:</span> <code>FAILURE_INJECTION_PROB=0.1</code>
              </div>
              <div className="px-3 py-1 rounded bg-zinc-800 ring-1 ring-zinc-700">
                <span className="font-semibold">Rate Limit:</span> <code>RATE_LIMIT</code>
              </div>
            </div>
          </div>
        </m.div>

        {health === "down" && (
          <div className="mb-6 px-4 py-2 bg-yellow-600/90 text-sm rounded text-center">
            Backend unreachable — refresh karke try karein.
          </div>
        )}

        {/* Cards row - centered both axes */}
        <div className="flex flex-col lg:flex-row gap-6 justify-center items-stretch">
          {/* Backend Health */}
          <div className="flex-1 flex justify-center">
            <m.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="w-full"
            >
              <Card className="w-full backdrop-blur border shadow-lg bg-gradient-to-tr from-slate-800 to-zinc-800 border-zinc-700">
                <CardContent className="p-6">
                  <div className="flex flex-col sm:flex-row items-start justify-between mb-4 gap-4">
                    <div className="flex items-center gap-3">
                      <Server className="h-6 w-6 text-cyan-300" />
                      <div>
                        <div className="text-xs uppercase tracking-wide text-slate-400">Backend Health</div>
                        <div
                          className={`text-xl font-semibold mt-1 ${
                            health === "ok" ? "text-emerald-500" : "text-rose-500"
                          }`}
                        >
                          {health === "ok" ? "OK" : "DOWN"}
                        </div>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => window.location.reload()}
                      className="flex items-center gap-1 hover:scale-105 transition"
                    >
                      <RefreshCw className="h-4 w-4" /> Refresh
                    </Button>
                  </div>
                  <div className="rounded-xl overflow-hidden ring-1 ring-zinc-700">
                    <SpinningGem />
                  </div>
                </CardContent>
              </Card>
            </m.div>
          </div>

          {/* Failure Probability */}
          <div className="flex-1 flex justify-center">
            <m.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="w-full"
            >
              <Card className="w-full backdrop-blur border shadow-lg bg-gradient-to-tr from-slate-800 to-zinc-800 border-zinc-700">
                <CardContent className="p-6 flex flex-col items-center">
                  <div className="text-center mb-3">
                    <div className="inline-flex items-center gap-2">
                      <Gauge className="h-6 w-6 text-pink-400" />
                      <span className="text-sm font-semibold">Failure Probability</span>
                    </div>
                  </div>
                  <div className="h-44 flex items-center justify-center">
                    <RadialBarChart
                      width={200}
                      height={200}
                      data={radialData}
                      innerRadius="60%"
                      outerRadius="100%"
                      startAngle={180}
                      endAngle={0}
                    >
                      <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                      <RadialBar
                        dataKey="value"
                        cornerRadius={10}
                        fill={highRisk ? "#fb7185" : "#22c55e"}
                      />
                    </RadialBarChart>
                  </div>
                  <div className="text-center mt-2">
                    <div className="text-4xl font-bold">{prob == null ? "--" : `${Math.round(prob * 100)}%`}</div>
                    <div
                      className={`text-sm font-medium mt-1 ${
                        highRisk ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {prob == null ? "Predict" : highRisk ? "High Risk" : "OK"}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </m.div>
          </div>

          {/* Input Features + Predict */}
          <div className="flex-1 flex justify-center">
            <m.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="w-full"
            >
              <Card className="w-full backdrop-blur border shadow-lg bg-gradient-to-tr from-slate-800 to-zinc-800 border-zinc-700">
                <CardContent className="p-6">
                  <div className="text-center mb-4">
                    <div className="inline-flex items-center gap-2">
                      <Play className="h-6 w-6 text-green-400" />
                      <span className="text-lg font-semibold">Input Features</span>
                    </div>
                    <div className="text-xs text-slate-300 mt-1">Values ko update karke Predict dabayein</div>
                  </div>

                  <div className="grid gap-3 justify-items-center">
                    {Object.entries(features).map(([k, v]) => (
                      <div key={k} className="w-full grid grid-cols-1 sm:grid-cols-2 items-center gap-2">
                        <label className="text-xs sm:text-right capitalize pr-2">{k.replaceAll("_", " ")}?</label>
                        <Input
                          className="bg-zinc-800 border border-slate-700 text-slate-100 w-full"
                          type="number"
                          step="any"
                          value={v}
                          onChange={(e) => update(k, Number(e.target.value))}
                        />
                      </div>
                    ))}
                    <div className="w-full grid grid-cols-1 sm:grid-cols-2 items-center gap-2">
                      <label className="text-xs sm:text-right pr-2">threshold?</label>
                      <Input
                        className="bg-zinc-800 border border-slate-700 text-slate-100 w-full"
                        type="number"
                        step="0.01"
                        value={threshold}
                        onChange={(e) => setThreshold(clampThreshold(Number(e.target.value)))}
                      />
                    </div>
                  </div>

                  <div className="mt-5 flex justify-center">
                    <Button disabled={loading} onClick={doPredict} className="w-full max-w-xs hover:scale-105 transition">
                      {loading ? "Predicting…" : "Predict"}
                    </Button>
                  </div>

                  {err && (
                    <div className="mt-3 text-center text-xs text-rose-400 bg-[#3a1f2e] px-3 py-1 rounded">
                      {err}
                    </div>
                  )}
                </CardContent>
              </Card>
            </m.div>
          </div>
        </div>
      </div>
    </div>
  );
}
