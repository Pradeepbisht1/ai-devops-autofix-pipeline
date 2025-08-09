# AI‑DevOps: Predict, Deploy & Auto‑Heal Pipeline

End‑to‑end, production‑grade example that builds a **ML‑driven risk predictor**, deploys a **backend + frontend** on **Amazon EKS**, scrapes runtime metrics via **Prometheus**, and **auto‑heals** your app when predicted risk crosses a threshold (with optional **rollback** and **Slack alerts**).

---

## Table of Contents

- [AI‑DevOps: Predict, Deploy \& Auto‑Heal Pipeline](#aidevops-predict-deploy--autoheal-pipeline)
  - [Table of Contents](#table-of-contents)
  - [Architecture](#architecture)
  - [Repository Layout](#repository-layout)
  - [Features](#features)
  - [Requirements](#requirements)
  - [One‑Time AWS/EKS Setup](#onetime-awseks-setup)
  - [GitHub Secrets](#github-secrets)
  - [Local Development](#local-development)
    - [Backend (Flask API)](#backend-flask-api)
    - [Frontend (Risk Dashboard)](#frontend-risk-dashboard)
  - [Kubernetes Manifests](#kubernetes-manifests)
  - [Prometheus \& Metrics](#prometheus--metrics)
  - [GitHub Actions Pipeline](#github-actions-pipeline)
    - [What it does](#what-it-does)
    - [Risk → Auto‑Heal Flow](#risk--autoheal-flow)
    - [Tuning Risk Threshold](#tuning-risk-threshold)
  - [RBAC \& aws‑auth Mapping](#rbac--awsauth-mapping)
  - [Operational Playbook](#operational-playbook)
  - [Troubleshooting](#troubleshooting)
  - [Security \& Prod Hardening](#security--prod-hardening)
  - [Cost \& Cleanup](#cost--cleanup)
  - [License](#license)

---

## Architecture

```
Developer Push ─────────────► GitHub Actions
     │                           │
     │                           ├── Build images (backend, frontend) → push to Amazon ECR
     │                           ├── kubectl apply (services, deployments, HPA, Ingress)
     │                           ├── LoadGen (optional) to keep traffic flowing
     │                           ├── Port‑forward Prometheus → pull runtime metrics
     │                           ├── Call /predict on backend with features from PromQL
     │                           └── If p >= threshold: auto‑heal + re‑check → rollback if needed
     │
   Users ──► ALB/Ingress ──► Frontend (React/Vite) ──► Backend (Flask)
                                 │                       │
                                 │                       ├── /healthz
                                 │                       └── /predict  (ML model.pkl)
                                 │
                         Prometheus Operator ──► ServiceMonitor (scrape backend /metrics)
```

- **Namespace**: `prod`
- **Deployments**: `backend`, `frontend`
- **Services**: `backend` (ClusterIP:5000), `frontend` (LB:80 or via Ingress/ALB)
- **Ingress**: `kubernetes.io/ingress.class: alb` (internet‑facing)
- **Prometheus**: Expects an existing Prometheus Operator svc `prometheus-operated` in `monitoring`
- **Auto‑heal**: `pipeline/scripts/smart_auto_heal.py`
- **Model**: `ml_model/models/model.pkl` (committed binary, **not** a Git‑LFS pointer)

---

## Repository Layout

```
.
├─ app/                         # Backend (Flask, /healthz, /predict)
├─ dashboard/                   # Frontend (React/Vite dashboard)
├─ kubernetes/                  # Manifests (svc, deploy, HPA, ServiceMonitor, RBAC, ingress)
│  ├─ backend-deploy.yaml
│  ├─ backend-svc.yaml
│  ├─ backend-servicemonitor.yaml
│  ├─ frontend-deploy.yaml
│  ├─ frontend-svc.yaml
│  ├─ hpa-backend.yaml
│  ├─ hpa-frontend.yaml
│  ├─ ingress.yaml
│  ├─ gha-*.yaml                # RBAC helpers for CI + Prometheus upgrades
│  └─ namespace.yaml
├─ pipeline/
│  └─ scripts/
│     └─ smart_auto_heal.py     # Restart → cache clear+restart → rollback (with Slack)
├─ ml_model/
│  └─ models/model.pkl          # Binary model file (no LFS pointer)
├─ tests/
├─ fetch_features.sh            # Helper to pull features from Prometheus (optional)
├─ requirements.txt
└─ .github/workflows/ci.yml     # GitHub Actions (see below)
```

---

## Features

- CI/CD from GitHub → **ECR/EKS** with sane concurrency & timeouts
- **Prometheus** feature collection with port‑forward (no public Prometheus needed)
- **ML‑based risk score** from real runtime signals
- **Auto‑heal playbook** with 3 steps:
  1. Restart + scale
  2. Cache clear inside pod + restart + scale
  3. Rollback
- **Slack notifications** for heal/rollback/kept
- **HPA**, **ServiceMonitor**, **Ingress/ALB** ready
- Hardened resource requests/limits; readable manifests

---

## Requirements

- **AWS**: EKS cluster, access to create ECR repos
- **IAM**: A role for GitHub OIDC (`AWS_ROLE_ARN`), and appropriate Kubernetes RBAC (below)
- **Prometheus Operator** installed (`monitoring` namespace), service `prometheus-operated`
- **GitHub**: repository with Actions enabled, secrets configured

---

## One‑Time AWS/EKS Setup

1. **ECR repos** (CI will create if missing):  
   `myapp` (backend) and `ai-devops-frontend` (frontend)

2. **EKS & OIDC role for GitHub**:  
   Create a role with trust to GitHub OIDC provider, attach AWS permissions to push to ECR and update EKS.

3. **Map role/user in `aws-auth`** (Kubernetes):  
   ```yaml
   # kube-system/aws-auth ConfigMap (snippet)
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::<ACCOUNT_ID>:role/github-actions-role
         username: gha
         groups:
           - github:ci
   ```

4. **RBAC in cluster** – see **[RBAC & aws‑auth Mapping](#rbac--aws-auth-mapping)**.

---

## GitHub Secrets

Configure in **Settings → Secrets and variables → Actions**:

- `AWS_DEFAULT_REGION` (e.g., `ap-southeast-2`)
- `AWS_ACCOUNT_ID`
- `EKS_CLUSTER_NAME`
- `AWS_ROLE_ARN` (GitHub OIDC role to assume)
- `SLACK_WEBHOOK_URL` (optional, for alerts)
- `MODEL_S3_PATH` (optional, if you want to copy model to S3 after build)

---

## Local Development

### Backend (Flask API)

Assumes a model at `ml_model/models/model.pkl` and a Flask app exposing:

- `GET /healthz`
- `POST /predict` with JSON body:
  ```json
  {
    "restart_count_last_5m": 0,
    "cpu_usage_pct": 0.65,
    "memory_usage_bytes": 52428800,
    "ready_replica_ratio": 1.0,
    "unavailable_replicas": 0,
    "network_receive_bytes_per_s": 86,
    "http_5xx_error_rate": 0
  }
  ```

Run locally:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PORT=5000 MODEL_PATH=ml_model/models/model.pkl
python app/main.py
curl -s http://127.0.0.1:5000/healthz
```

### Frontend (Risk Dashboard)

- The dashboard defaults to `VITE_API_BASE=http://localhost:5000`.
- Build & run (Vite):
  ```bash
  cd dashboard
  npm ci
  npm run dev   # or npm run build && npm run preview
  ```

---

## Kubernetes Manifests

Key defaults (namespace `prod`):

- **backend**: `kubernetes/backend-deploy.yaml`  
  - Ports: 5000 (`name: http`)
  - Probes: `/healthz`
  - Resources: requests 200m/256Mi, limits 1/1Gi
- **frontend**: `kubernetes/frontend-deploy.yaml`  
  - Ports: 80
- **ServiceMonitor**: `kubernetes/backend-servicemonitor.yaml`  
  - Path: `/metrics`, port: `http`, interval: `15s`
- **HPA**: `kubernetes/hpa-*.yaml`  
  - backend (2..6), cpu avgUtilization 60%
- **Ingress (ALB)**: `kubernetes/ingress.yaml`  
  - Annotated with `kubernetes.io/ingress.class: alb`

Apply manually (if needed):
```bash
kubectl apply -n prod -f kubernetes/
```

Get Ingress URL:
```bash
kubectl -n prod get ingress web -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

---

## Prometheus & Metrics

- This repo expects a **Prometheus Operator** in `monitoring` with svc `prometheus-operated`.
- The pipeline **port‑forwards** the Prometheus API on 9090 to query runtime metrics, e.g.:
  - CPU:  
    `rate(container_cpu_usage_seconds_total{namespace="prod",pod=~"backend-.*",container!="POD"}[2m]) * 100`
  - Memory:  
    `avg(container_memory_working_set_bytes{namespace="prod",pod=~"backend-.*",container!="POD"})`
  - Restarts (5m):  
    `increase(kube_pod_container_status_restarts_total{namespace="prod",pod=~"backend-.*"}[5m])`
  - HTTP 5xx:  
    `sum(rate(flask_http_request_total{status=~"5..",namespace="prod",pod=~"backend-.*"}[2m]))`

The features are aggregated with `jq` to a JSON body and POSTed to `/predict`.

---

## GitHub Actions Pipeline

File: `.github/workflows/ci.yml` (name: **Predict, Deploy & Auto‑Heal Pipeline**)

### What it does

1. Verify model binary (no LFS pointer)
2. Login to ECR
3. Build & push backend and frontend images
4. Apply/Update K8s manifests (svc, deploy, HPA, ServiceMonitor, Ingress)
5. Wait for rollouts
6. Deploy a small **loadgen** to keep traffic flowing
7. **Port‑forward Prometheus**, query metrics → build features JSON
8. Port‑forward **backend** and call `/predict`
9. If **probability ≥ `RISK_THRESHOLD`** (default **0.50**): trigger **auto‑healing**
10. Re‑check risk after **120s**:
    - If still high → **rollback**
    - Else → keep rollout
11. Slack notifications (optional)
12. Cleanup temp resources

### Risk → Auto‑Heal Flow

- Step 0 (first time high): **restart + scale**
- Step 1 (if high again): **clear cache in pod** + restart + scale
- Step 2 (if high again): **rollback** to previous ReplicaSet
- Attempts are tracked via a deployment annotation: `healing.attempt`

Script: `pipeline/scripts/smart_auto_heal.py`

```text
Attempt 1 → restart + scale
Attempt 2 → clear cache + restart + scale
Attempt 3 → rollback
```

### Tuning Risk Threshold

In workflow env:
```yaml
env:
  RISK_THRESHOLD: "0.50"
```

- Use **`0.70`** or above for stricter healing.
- For testing, set lower threshold to exercise auto‑heal logic.

---

## RBAC & aws‑auth Mapping

1. **Map GitHub OIDC role to Kubernetes user** in `aws-auth`:
   ```yaml
   data:
     mapRoles: |
       - rolearn: arn:aws:iam::<ACCOUNT_ID>:role/github-actions-role
         username: gha
         groups:
           - github:ci
   ```

2. **Give CI the app‑namespace permissions** (example for `prod`):  
   `kubernetes/gha-rbac.yaml` should define a Role with safe verbs for deploys and scaling:

   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: gh-actions-app-access
     namespace: prod
   rules:
     # Deployments & ReplicaSets (set image, rollout status/undo, scale)
     - apiGroups: ["apps"]
       resources: ["deployments", "deployments/scale", "replicasets"]
       verbs: ["get","list","watch","update","patch","create"]

     # Services/Endpoints (for apply + port-forward svc)
     - apiGroups: [""]
       resources: ["services","endpoints"]
       verbs: ["get","list","watch","create","update","patch"]

     # Read‑only pods + logs/status
     - apiGroups: [""]
       resources: ["pods","pods/log","pods/status"]
       verbs: ["get","list","watch"]

     # Allow port‑forward/exec (needed for cache‑clear step & port‑forward)
     - apiGroups: [""]
       resources: ["pods/portforward","pods/exec"]
       verbs: ["create"]

     - apiGroups: [""]
       resources: ["events"]
       verbs: ["get","list","watch"]
   ```

   Bind to GitHub identity:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: gh-actions-app-access-rb
     namespace: prod
   subjects:
     - kind: User
       name: gha
       apiGroup: rbac.authorization.k8s.io
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: Role
     name: gh-actions-app-access
   ```

   If you want to **centralize `pods/exec`** across namespaces, create a **ClusterRole** and bind **per namespace**:
   ```yaml
   apiVersion: rbac.authorization.k8s.io/v1
   kind: ClusterRole
   metadata:
     name: allow-pod-exec
   rules:
     - apiGroups: [""]
       resources: ["pods","pods/log","pods/exec","pods/portforward"]
       verbs: ["get","list","watch","create"]
   ---
   apiVersion: rbac.authorization.k8s.io/v1
   kind: RoleBinding
   metadata:
     name: allow-pod-exec-rb
     namespace: prod
   subjects:
     - kind: User
       name: gha
       apiGroup: rbac.authorization.k8s.io
   roleRef:
     apiGroup: rbac.authorization.k8s.io
     kind: ClusterRole
     name: allow-pod-exec
   ```

3. **Quick checks** (from your terminal):
```bash
kubectl auth can-i patch deployments/scale -n prod --as=gha
kubectl auth can-i create pods/exec        -n prod --as=gha
kubectl auth can-i create pods/portforward -n prod --as=gha
```

---

## Operational Playbook

- **Find the ALB hostname**:
  ```bash
  H=$(kubectl -n prod get ingress web -o jsonpath='{.status.loadBalancer.ingress[0].hostname}');
  echo "http://$H/"
  ```

- **Backend health**:
  ```bash
  kubectl -n prod port-forward svc/backend 5000:5000 &
  curl -s http://127.0.0.1:5000/healthz
  ```

- **Manual prediction**:
  ```bash
  curl -s -X POST http://127.0.0.1:5000/predict -H 'Content-Type: application/json' -d '{
    "restart_count_last_5m": 0,
    "cpu_usage_pct": 10,
    "memory_usage_bytes": 52428800,
    "ready_replica_ratio": 1,
    "unavailable_replicas": 0,
    "network_receive_bytes_per_s": 86,
    "http_5xx_error_rate": 0
  }'
  ```

- **Force a rollback**:
  ```bash
  kubectl -n prod rollout undo deployment/backend
  ```

- **Reset auto‑heal attempt annotation**:
  ```bash
  kubectl -n prod annotate deployment/backend healing.attempt-
  ```

---

## Troubleshooting

- **Ingress shows empty hostname**: ensure AWS Load Balancer Controller is installed & Ingress class is `alb`.
- **Prometheus “no targets”**: check `ServiceMonitor` label selectors and that backend Service port is named `http`.
- **`/predict` errors**: verify `MODEL_PATH`, confirm `model.pkl` is a real binary (the pipeline checks this).
- **`pods/exec` forbidden**: align `aws-auth` mappings and RBAC Role/RoleBinding (see [RBAC](#rbac--aws-auth-mapping)).
- **Slack 404**: make sure webhook URL is correct (Slack App/Incoming Webhook).

---

## Security & Prod Hardening

- Minimize CI RBAC: limit to `prod` namespace and only verbs you need.
- Network policies for Prometheus to scrape only what’s needed.
- Protect `/metrics` (service annotations, mTLS, or network policies if applicable).
- Image provenance (signing/verification with cosign).
- Rotate Slack webhook, store in Actions secrets.
- Pin `kubectl` and base images (already pinned in pipeline).

---

## Cost & Cleanup

- **ALB/ELB**, public IPs, and `LoadBalancer` services cost money.  
  Use `ClusterIP + Ingress` where possible.
- Cleanup demo load generator:
  ```bash
  kubectl -n prod delete deploy/loadgen --ignore-not-found
  ```
- Delete ECR images not used by running workloads.

---

## License

MIT (or your org’s standard). Update as required.

---

> **Tip**: For quick end‑to‑end test in a fresh cluster, run the GitHub Action manually (workflow_dispatch) and watch the logs for **Predict → Auto‑Heal → Re‑check** transitions.
 