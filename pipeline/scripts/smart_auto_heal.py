#!/usr/bin/env python3
import subprocess
import sys
import argparse
import requests
import time
import os

MAX_ATTEMPTS = 3
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # Secure via GitHub Secret or ENV

def run_cmd(cmd, capture_output=False):
    print(f"> {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True, capture_output=capture_output, text=True)
    return result.stdout.strip() if capture_output else None

def get_attempt(deployment, namespace):
    try:
        result = run_cmd([
            "kubectl", "get", "deployment", deployment,
            "-n", namespace,
            "-o", "jsonpath={.metadata.annotations.healing\\.attempt}"
        ], capture_output=True)
        return int(result) if result else 0
    except:
        return 0

def set_attempt(deployment, namespace, attempt):
    run_cmd([
        "kubectl", "annotate", "deployment", deployment,
        f"healing.attempt={attempt}", "--overwrite", "-n", namespace
    ])

def restart_and_scale(deployment, namespace, replicas):
    print("[STEP] Restarting deployment and scaling replicas")
    run_cmd(["kubectl", "rollout", "restart", f"deployment/{deployment}", "-n", namespace])
    run_cmd(["kubectl", "scale", "deployment", deployment,
             f"--replicas={replicas}", "-n", namespace])
    run_cmd(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace])

def clear_cache_inside_pod(deployment, namespace):
    print("[STEP] Attempting cache clear inside pod...")
    try:
        pod_name = run_cmd([
            "kubectl", "get", "pods", "-n", namespace,
            "-l", f"app={deployment}", "-o", "jsonpath={.items[0].metadata.name}"
        ], capture_output=True)
        run_cmd([
            "kubectl", "exec", pod_name, "-n", namespace, "--", "rm", "-rf", "/tmp/*"
        ])
        print("[INFO] Cache cleared inside pod.")
    except Exception as e:
        print(f"[WARN] Cache clear step failed: {e}")

def rollback(deployment, namespace):
    print("[STEP] Rolling back deployment...")
    run_cmd(["kubectl", "rollout", "undo", f"deployment/{deployment}", "-n", namespace])
    run_cmd(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace])

def send_slack_alert(deployment):
    if not SLACK_WEBHOOK_URL:
        print("[WARN] SLACK_WEBHOOK_URL is not set. Skipping alert.")
        return

    print("[ALERT] Sending Slack failure alert")
    message = {
        "text": f":rotating_light: *Auto-healing failed* for deployment `{deployment}` after {MAX_ATTEMPTS} attempts. Manual intervention needed."
    }
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json=message)
        if r.status_code == 200:
            print("[INFO] Slack alert sent.")
        else:
            print(f"[ERROR] Failed to send Slack alert: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Slack alert failed: {e}")

def retry(action_func, retries=2, wait=3):
    for attempt in range(1, retries + 1):
        try:
            action_func()
            return
        except Exception as e:
            print(f"[WARN] Attempt {attempt} failed: {e}")
            time.sleep(wait)
    raise RuntimeError("All retries failed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--replicas", type=int, default=3)
    args = parser.parse_args()

    deployment = args.deployment
    ns = args.namespace
    replicas = args.replicas

    attempt = get_attempt(deployment, ns)
    print(f"[INFO] Healing attempt: {attempt + 1}")

    if attempt >= MAX_ATTEMPTS:
        print("[ERROR] Max healing attempts reached.")
        send_slack_alert(deployment)
        sys.exit(2)

    try:
        if attempt == 0:
            retry(lambda: restart_and_scale(deployment, ns, replicas))
        elif attempt == 1:
            retry(lambda: clear_cache_inside_pod(deployment, ns))
            retry(lambda: restart_and_scale(deployment, ns, replicas))
        elif attempt == 2:
            retry(lambda: rollback(deployment, ns))
    except Exception as e:
        print(f"[ERROR] Healing failed at step {attempt + 1}: {e}")
        send_slack_alert(deployment)
        sys.exit(2)

    set_attempt(deployment, ns, attempt + 1)
    print("[INFO] Healing step complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()
