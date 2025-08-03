import { useEffect, useState } from "react";
import { fetchHealth } from "../services/api";

export default function HealthBadge() {
  const [status, setStatus] = useState("loading");
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  const refresh = async () => {
    try {
      const h = await fetchHealth();
      setInfo(h);
      if (h.model_loaded) setStatus("ok");
      else if (h.model_error) setStatus("degraded");
      else setStatus("unknown");
    } catch (e) {
      setError(e.message);
      setStatus("down");
    }
  };

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 30000);
    return () => clearInterval(iv);
  }, []);

  const color =
    status === "ok"
      ? "text-green-700 bg-green-100"
      : status === "degraded"
      ? "text-yellow-800 bg-yellow-100"
      : status === "down"
      ? "text-red-700 bg-red-100"
      : "text-gray-700 bg-gray-100";

  return (
    <div className={`px-3 py-1 rounded flex items-center gap-2 ${color}`}>
      <div className="text-xs font-medium">
        {status === "ok" && "Model loaded"}
        {status === "degraded" && "Fallback/Issue"}
        {status === "down" && "Backend down"}
        {status === "unknown" && "Initializing"}
        {status === "loading" && "Loading..."}
      </div>
    </div>
  );
}
