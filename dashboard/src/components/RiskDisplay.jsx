export default function RiskDisplay({ result }) {
  const threshold = parseFloat(import.meta.env.VITE_RISK_HIGH_THRESHOLD || "0.7");
  const isHigh = result.probability >= threshold;

  return (
    <div className="flex flex-col items-start gap-1">
      <div className="flex items-center gap-2">
        <div
          className={`px-3 py-1 rounded text-sm font-semibold ${
            isHigh ? "bg-red-500 text-white" : "bg-green-500 text-white"
          }`}
        >
          {result.risk}
        </div>
        <div className="text-sm">
          {(result.probability * 100).toFixed(1)}%
        </div>
      </div>
      <div className="text-xs text-gray-600">Threshold: {(threshold * 100).toFixed(1)}%</div>
    </div>
  );
}
