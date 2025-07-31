import numpy as np
import pandas as pd
import argparse

def generate_synthetic(n_samples=100_000, seed=42):
    np.random.seed(seed)

    # Base healthy distributions
    cpu = np.clip(np.random.normal(loc=30, scale=10, size=n_samples), 0, 100)  # percent
    mem = np.clip(np.random.normal(loc=200 * 1024**2, scale=50 * 1024**2, size=n_samples), 50 * 1024**2, None)  # bytes
    ready_ratio = np.clip(np.random.beta(a=20, b=2, size=n_samples), 0, 1)  # near 1 when healthy
    unavailable = np.random.poisson(lam=0.1, size=n_samples)  # usually zero
    net_recv = np.clip(np.random.exponential(scale=1000, size=n_samples), 0, None)  # bytes/s
    error_5xx = np.clip(np.random.beta(a=1, b=50, size=n_samples), 0, 1)  # small when healthy
    restarts = np.random.poisson(lam=0.05, size=n_samples)  # few restarts

    # Introduce degraded/failure cases by randomly boosting some samples
    is_degraded = np.random.rand(n_samples) < 0.1  # 10% are degraded candidates

    cpu[is_degraded] = np.clip(np.random.normal(loc=75, scale=15, size=is_degraded.sum()), 0, 100)
    mem[is_degraded] = np.clip(np.random.normal(loc=500 * 1024**2, scale=100 * 1024**2, size=is_degraded.sum()), 100 * 1024**2, None)
    ready_ratio[is_degraded] = np.clip(np.random.beta(a=2, b=5, size=is_degraded.sum()), 0, 1)
    unavailable[is_degraded] = np.random.poisson(lam=2, size=is_degraded.sum())
    net_recv[is_degraded] = np.clip(np.random.exponential(scale=5000, size=is_degraded.sum()), 0, None)
    error_5xx[is_degraded] = np.clip(np.random.beta(a=5, b=10, size=is_degraded.sum()), 0, 1)
    restarts[is_degraded] = np.random.poisson(lam=3, size=is_degraded.sum())

    # Construct failure probability heuristic (you'll replace with actual model labels)
    score = (
        0.3 * (cpu / 100) +
        0.2 * (mem / (1024**3)) +  # scaled
        0.2 * (1 - ready_ratio) +
        0.1 * (unavailable / (unavailable + 1)) +
        0.1 * error_5xx +
        0.1 * np.clip(restarts / 5, 0, 1)
    )
    # Normalize
    score = score / score.max()

    # Threshold to get label; add randomness to simulate noise
    failure_prob = score * 0.7 + np.random.normal(0, 0.05, size=n_samples)
    failure = (failure_prob > 0.5).astype(int)

    df = pd.DataFrame({
        "restart_count_last_5m": restarts,
        "cpu_usage_percent": cpu,
        "memory_usage_bytes": mem,
        "ready_replica_ratio": ready_ratio,
        "unavailable_replicas": unavailable,
        "network_receive_bytes_per_s": net_recv,
        "http_5xx_error_rate": error_5xx,
        "failure": failure,
    })

    return df

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Prometheus feature data.")
    parser.add_argument("--samples", type=int, default=100_000, help="Number of rows to generate.")
    parser.add_argument("--out", type=str, default="prom_features.csv", help="Output CSV path.")
    args = parser.parse_args()

    df = generate_synthetic(n_samples=args.samples)
    df.to_csv(args.out, index=False)
    print(f"Written {len(df)} rows to {args.out}")

if __name__ == "__main__":
    main()
