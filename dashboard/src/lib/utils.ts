export function formatPercent(p: number): string {
  return `${(p * 100).toFixed(1)}%`;
}

export function riskColor(risk: string): string {
  if (risk === "HIGH") return "text-red-600";
  if (risk === "LOW") return "text-green-600";
  return "text-gray-600";
}
