#!/usr/bin/env python3
import subprocess
import sys
import argparse
import requests
import time
import os

MAX_ATTEMPTS = 3
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # from GitHub Secret or ENV

def run_cmd(cmd, capture_output=False):
    print(f"> {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True, capture_output=capture_output, text=True)
    return result.stdout.strip() if capture_output else None

def get_attempt(deployment, namespace):
    try:
        out = run_cmd([
            "kubectl", "get", "deployment", deployment,
            "-n", namespace,
            "-o", "jsonpath={.metadata.annotations.healing\\.attempt}"
        ], capture_output=True)
        return int(out) if out else 0
    except Exception:
        return 0

def set_attempt(deployment, namespace, attempt):
    run_cmd([
        "kubectl", "annotate", "deployment", deployment,
        f"healing.attempt={attempt}", "--overwrite", "-n", namespace
    ])

def restart_and_scale(deployment, namespace, replicas):
    print("[STEP] Restarting deployment and scaling replicas")
    run_cmd(["kubectl", "rollout", "restart", f"deployment/{deployment}", "-n", namespace])
    run_cmd(["kubectl", "scale", "deployment", deployment, f"--replicas={replicas}", "-n", namespace])
    run_cmd(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace, "--timeout=5m"])

def clear_cache_inside_pod(deployment, namespace, container=None):
    print("[STEP] Attempting cache clear inside pod...")
    try:
        pod = run_cmd([
            "kubectl", "get", "pods", "-n", namespace,
            "-l", f"app={deployment}",
            "-o", "jsonpath={.items[0].metadata.name}"
        ], capture_output=True)
        cmd = ["kubectl", "exec", pod, "-n", namespace]
        if container:
            cmd += ["-c", container]
        cmd += ["--", "sh", "-lc", "rm -rf /tmp/* || true"]
        run_cmd(cmd)
        print("[INFO] Cache cleared inside pod.")
    except Exception as e:
        print(f"[WARN] Cache clear step failed: {e}")

def rollback(deployment, namespace):
    print("[STEP] Rolling back deployment...")
    run_cmd(["kubectl", "rollout", "undo", f"deployment/{deployment}", "-n", namespace])
    run_cmd(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace, "--timeout=5m"])

def send_slack_alert(text):
    if not SLACK_WEBHOOK_URL:
        print("[WARN] SLACK_WEBHOOK_URL is not set. Skipping Slack alert.")
        return
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": text})
        if r.status_code == 200:
            print("[INFO] Slack alert sent.")
        else:
            print(f"[ERROR] Slack alert failed: HTTP {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Slack alert exception: {e}")

def retry(action_func, retries=2, wait=3):
    for i in range(1, retries + 1):
        try:
            action_func()
            return
        except Exception as e:
            print(f"[WARN] Attempt {i} failed: {e}")
            time.sleep(wait)
    raise RuntimeError("All retries failed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--namespace", default="default")
    parser.add_argument("--replicas", type=int, default=3)
    parser.add_argument("--container", default=None, help="container name for exec steps (optional)")
    args = parser.parse_args()

    deployment = args.deployment
    ns = args.namespace
    replicas = args.replicas

    attempt = get_attempt(deployment, ns)
    print(f"[INFO] Healing attempt: {attempt + 1}")

    if attempt >= MAX_ATTEMPTS:
        msg = f":rotating_light: Auto-heal *aborted*: reached max attempts ({MAX_ATTEMPTS}) for `{deployment}` in `{ns}`."
        print("[ERROR] " + msg)
        send_slack_alert(msg)
        sys.exit(2)

    try:
        if attempt == 0:
            retry(lambda: restart_and_scale(deployment, ns, replicas))
        elif attempt == 1:
            retry(lambda: clear_cache_inside_pod(deployment, ns, args.container))
            retry(lambda: restart_and_scale(deployment, ns, replicas))
        elif attempt == 2:
            retry(lambda: rollback(deployment, ns))
    except Exception as e:
        msg = f":rotating_light: Auto-heal step {attempt + 1} *failed* for `{deployment}` in `{ns}`: {e}"
        print("[ERROR] " + msg)
        send_slack_alert(msg)
        sys.exit(2)

    # record that we escalated one step this run
    set_attempt(deployment, ns, attempt + 1)
    print("[INFO] Healing step complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()
