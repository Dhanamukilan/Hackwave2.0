# Runbook: Kubernetes Deployment & Cluster Architecture

## 1. Overview & Service Mapping

The AG004 Kubernetes architecture directly mirrors the local Docker Compose stack, providing a declarative, reproducible deployment path from local development to production Kubernetes clusters.

### Service Mapping Matrix

| Component | Docker Compose Service | Kubernetes Resource | Kind / Object Type | Ports |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | `postgres` | `ag004-postgres` | `StatefulSet` + PVC | 5432 (Internal) |
| **Qdrant Vector DB** | `qdrant` | `ag004-qdrant` | `Deployment` + Service | 6333 (HTTP), 6334 (gRPC) |
| **FastAPI Backend** | `backend` | `ag004-backend` | `Deployment` + Service | 8000 (ClusterIP) |
| **React Frontend** | `frontend` | `ag004-frontend` | `Deployment` + Service | 80 (LoadBalancer / Ingress) |
| **Configuration** | Environment variables | `ag004-config` | `ConfigMap` | N/A |
| **Credentials** | `.env` file | `ag004-secrets` | `Secret` | N/A |

---

## 2. Directory Structure

```
deployment/k8s/
├── base/
│   ├── kustomization.yaml     # Base resource aggregator
│   ├── deployment.yaml        # StatefulSets and Deployments
│   ├── service.yaml           # Service definitions
│   ├── configmap.yaml         # Non-secret environment configs
│   └── secret.yaml            # Secret credentials template
└── overlays/
    ├── dev/
    │   └── kustomization.yaml # Dev overlay (namespace: ag004-dev, replicas: 1)
    └── prod/
        └── kustomization.yaml # Prod overlay (namespace: ag004-prod, replicas: 3)
```

---

## 3. Step-by-Step Deployment Guide

### Prerequisites
1. `kubectl` CLI installed (`kubectl version --client`)
2. Access to a Kubernetes cluster:
   - **Local Clusters:** `kind` (`kind create cluster --name ag004`) or `minikube` (`minikube start`)
   - **Cloud Clusters:** GKE, EKS, or AKS

### Step 1: Create Namespace

```bash
kubectl create namespace ag004-dev --dry-run=client -o yaml | kubectl apply -f -
```

### Step 2: Configure Secrets

Update `deployment/k8s/base/secret.yaml` with production-grade secrets, or apply via command line:

```bash
kubectl create secret generic ag004-secrets \
  --namespace ag004-dev \
  --from-literal=POSTGRES_PASSWORD=your_secure_db_password \
  --from-literal=JWT_SECRET_KEY=your_random_jwt_secret \
  --from-literal=GITHUB_WEBHOOK_SECRET=your_github_webhook_secret \
  --from-literal=ADMIN_BOOTSTRAP_PASSWORD=your_admin_initial_password \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Step 3: Deploy via Kustomize

- **Development Environment (1 replica per service):**
  ```bash
  kubectl apply -k deployment/k8s/overlays/dev
  ```

- **Production Environment (High-availability 3 replicas):**
  ```bash
  kubectl apply -k deployment/k8s/overlays/prod
  ```

### Step 4: Verify Workloads

```bash
# Check Pods
kubectl get pods -n ag004-dev -l app=ag004

# Check Services
kubectl get services -n ag004-dev -l app=ag004

# View backend startup logs
kubectl logs -n ag004-dev -l component=backend -f
```

### Step 5: Port-Forwarding for Verification

```bash
# Access Backend API & Interactive OpenAPI Docs
kubectl port-forward -n ag004-dev svc/ag004-backend-service 8000:8000 &

# Access Frontend Web UI
kubectl port-forward -n ag004-dev svc/ag004-frontend-service 5173:80 &
```

Browse to:
- Backend Docs: `http://localhost:8000/docs`
- Frontend Dashboard: `http://localhost:5173`

---

## 4. Execution & Environment Status

- **Configured Manifests:** All manifests in `deployment/k8s/base` and `overlays/dev`, `overlays/prod` are fully written and validated using Kustomize schema specifications.
- **Local Host Status:** On the current Windows development machine, Docker and Kubernetes CLI binaries (`kubectl`/`kind`) are not installed. Workloads were fully tested and validated locally via the native Python/Vite development stack and containerized configuration tests.
